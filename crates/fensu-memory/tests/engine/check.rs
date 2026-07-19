//! Direct-source validation and successful publication behavior.

use std::fs;

use fensu_memory::engine::main::check_memory::check_memory;

use crate::dependencies::helpers;
use crate::test_types::{FixtureFile, MemoryCheckTestCase};

#[test]
fn given_memory_sources_when_checking_then_returns_stable_findings_or_publishes_valid_corpus() {
    let test_cases = [
        MemoryCheckTestCase {
            description: "sorts structural, content, and graph findings without publication",
            files: &[
                FixtureFile {
                    path: ".ai/orphan.md",
                    contents: b"# Orphan\n",
                },
                FixtureFile {
                    path: ".ai/knowledge/repo/notes/20260717T120000_000000Z__NOTE-invalid.md",
                    contents: b"No title.\n",
                },
                FixtureFile {
                    path: ".ai/tasks/in-progress/20260717T120001_000000Z__FEAT-broken.md",
                    contents: b"# Broken\n\n- depends-on: [[missing-task]]\n",
                },
            ],
            expected_diagnostics: &[
                (
                    "MEM003",
                    ".ai/knowledge/repo/notes/20260717T120000_000000Z__NOTE-invalid.md",
                    Some(1),
                ),
                ("MEM002", ".ai/orphan.md", None),
                (
                    "MEM004",
                    ".ai/tasks/in-progress/20260717T120001_000000Z__FEAT-broken.md",
                    Some(3),
                ),
            ],
            expected_published: false,
        },
        MemoryCheckTestCase {
            description: "publishes one already-loaded valid corpus",
            files: &[FixtureFile {
                path: ".ai/knowledge/repo/notes/20260717T120002_000000Z__NOTE-valid.md",
                contents: b"# Valid\n\nRemember this.\n",
            }],
            expected_diagnostics: &[],
            expected_published: true,
        },
    ];
    for test_case in &test_cases {
        let root = helpers::write_repository(test_case.files);
        let database_path = root.join("memory.sqlite3");
        let result = check_memory(&root, &database_path).expect("memory check succeeds");
        let diagnostics: Vec<(&str, &str, Option<usize>)> = result
            .diagnostics
            .iter()
            .map(|diagnostic| {
                (
                    diagnostic.code,
                    diagnostic.repository_relative_path.as_str(),
                    diagnostic.line,
                )
            })
            .collect();

        assert_eq!(
            diagnostics, test_case.expected_diagnostics,
            "{}",
            test_case.description
        );
        assert_eq!(
            result.published.is_some(),
            test_case.expected_published,
            "{}",
            test_case.description
        );
        assert_eq!(
            database_path.exists(),
            test_case.expected_published,
            "{}",
            test_case.description
        );
        fs::remove_dir_all(root).expect("check repository is removable");
    }
}
