//! Walk behavior over rglob-parity fixtures.

use strata_facts::snapshot::main::walk_python_files::walk_python_files;

use crate::helpers;
use crate::test_types;

#[test]
fn given_fixture_trees_when_walking_then_matches_rglob_semantics() {
    let test_cases = [
        test_types::WalkTestCase {
            description: "matches nested python files and skips other suffixes",
            files: &[
                test_types::FixtureFile {
                    path: "root/pkg/a.py",
                    contents: "a = 1\n",
                },
                test_types::FixtureFile {
                    path: "root/pkg/deep/b.py",
                    contents: "b = 1\n",
                },
                test_types::FixtureFile {
                    path: "root/pkg/notes.txt",
                    contents: "text\n",
                },
                test_types::FixtureFile {
                    path: "root/README.md",
                    contents: "docs\n",
                },
            ],
            symlinks: &[],
            expected_entries: &[
                test_types::ExpectedEntry {
                    entry_suffix: "root/pkg/a.py",
                    expected_parts: Some(&["pkg", "a.py"]),
                },
                test_types::ExpectedEntry {
                    entry_suffix: "root/pkg/deep/b.py",
                    expected_parts: Some(&["pkg", "deep", "b.py"]),
                },
            ],
        },
        test_types::WalkTestCase {
            description: "matches directories named like python files and descends them",
            files: &[test_types::FixtureFile {
                path: "root/dir.py/inner.py",
                contents: "inner = 1\n",
            }],
            symlinks: &[],
            expected_entries: &[
                test_types::ExpectedEntry {
                    entry_suffix: "root/dir.py",
                    expected_parts: Some(&["dir.py"]),
                },
                test_types::ExpectedEntry {
                    entry_suffix: "root/dir.py/inner.py",
                    expected_parts: Some(&["dir.py", "inner.py"]),
                },
            ],
        },
        test_types::WalkTestCase {
            description: "traverses hidden directories and matches bare dot py names",
            files: &[
                test_types::FixtureFile {
                    path: "root/.hidden/h.py",
                    contents: "h = 1\n",
                },
                test_types::FixtureFile {
                    path: "root/.py",
                    contents: "",
                },
            ],
            symlinks: &[],
            expected_entries: &[
                test_types::ExpectedEntry {
                    entry_suffix: "root/.hidden/h.py",
                    expected_parts: Some(&[".hidden", "h.py"]),
                },
                test_types::ExpectedEntry {
                    entry_suffix: "root/.py",
                    expected_parts: Some(&[".py"]),
                },
            ],
        },
        test_types::WalkTestCase {
            description: "does not follow symlinked directories",
            files: &[test_types::FixtureFile {
                path: "outside/linked/c.py",
                contents: "c = 1\n",
            }],
            symlinks: &[test_types::FixtureSymlink {
                path: "root/linkdir",
                target: "outside/linked",
            }],
            expected_entries: &[],
        },
        test_types::WalkTestCase {
            description: "canonicalizes symlinked files and marks outside targets rootless",
            files: &[test_types::FixtureFile {
                path: "outside/target.py",
                contents: "t = 1\n",
            }],
            symlinks: &[test_types::FixtureSymlink {
                path: "root/link.py",
                target: "outside/target.py",
            }],
            expected_entries: &[test_types::ExpectedEntry {
                entry_suffix: "root/link.py",
                expected_parts: None,
            }],
        },
    ];
    for test_case in test_cases {
        let base = helpers::write_temp_tree(test_case.files, test_case.symlinks);
        let root = base.join("root");
        std::fs::create_dir_all(&root).expect("walk fixture root is writable");
        let walked = walk_python_files(&[root]);
        let per_root = walked.first().expect("one walked root is returned");
        let mut actual: Vec<(String, Option<Vec<String>>)> = per_root
            .iter()
            .map(|entry| {
                let suffix = entry
                    .entry_path
                    .strip_prefix(&base)
                    .expect("walked entries stay beneath the fixture base")
                    .to_string_lossy()
                    .into_owned();
                let parts = entry.root_relative_parts.as_ref().map(|parts| {
                    parts
                        .iter()
                        .map(|part| part.to_string_lossy().into_owned())
                        .collect()
                });
                (suffix, parts)
            })
            .collect();
        actual.sort();
        assert_eq!(
            actual,
            helpers::expected_rows(test_case.expected_entries),
            "{}",
            test_case.description
        );
        helpers::remove_temp_tree(&base);
    }
}

#[test]
fn given_symlinked_file_when_walking_then_reports_canonical_target() {
    let test_cases = [test_types::CanonicalTestCase {
        description: "canonical path follows the file symlink to its target",
        expected_canonical_suffix: "outside/target.py",
    }];
    for test_case in test_cases {
        let base = helpers::write_temp_tree(
            &[test_types::FixtureFile {
                path: "outside/target.py",
                contents: "t = 1\n",
            }],
            &[test_types::FixtureSymlink {
                path: "root/link.py",
                target: "outside/target.py",
            }],
        );
        let root = base.join("root");

        let walked = walk_python_files(&[root]);

        let entry = walked
            .first()
            .and_then(|entries| entries.first())
            .expect("the symlinked file is walked");
        let canonical = entry
            .canonical_path
            .as_ref()
            .expect("the symlinked file canonicalizes");
        assert_eq!(
            canonical,
            &base.join(test_case.expected_canonical_suffix),
            "{}",
            test_case.description
        );
        helpers::remove_temp_tree(&base);
    }
}
