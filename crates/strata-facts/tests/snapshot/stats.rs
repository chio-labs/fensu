//! Live repository stat batch behavior.

use std::fs;
use std::path::PathBuf;

use strata_facts::snapshot::main::observe_repository_stats::observe_repository_stats;
use strata_facts::snapshot::models::{RepositoryStatKind, RepositoryStatQuery};

use crate::helpers::{remove_temp_tree, write_temp_tree};
use crate::test_types::{FixtureFile, StatTestCase};

#[test]
fn given_repository_paths_when_observing_then_returns_metadata_in_order() {
    let test_cases = [StatTestCase {
        description: "returns existing and missing path metadata in query order",
        expected_answers: &[
            Some(("src/pkg/models.py", true)),
            Some(("src/pkg", true)),
            Some(("src/pkg/missing.py", false)),
        ],
    }];
    for test_case in test_cases {
        let root = write_temp_tree(
            &[FixtureFile {
                path: "src/pkg/models.py",
                contents: "VALUE: int = 1\n",
            }],
            &[],
        );
        let queries = vec![
            RepositoryStatQuery {
                relative_path: PathBuf::from("src/pkg/models.py"),
                kind: RepositoryStatKind::IsFile,
            },
            RepositoryStatQuery {
                relative_path: PathBuf::from("src/pkg"),
                kind: RepositoryStatKind::IsDir,
            },
            RepositoryStatQuery {
                relative_path: PathBuf::from("src/pkg/missing.py"),
                kind: RepositoryStatKind::Exists,
            },
        ];

        let answers = observe_repository_stats(&root, &queries);

        let actual: Vec<Option<(&str, bool)>> = answers
            .iter()
            .map(|answer| {
                answer
                    .as_ref()
                    .map(|value| (value.dependency_path.as_str(), value.answer))
            })
            .collect();
        assert_eq!(
            actual, test_case.expected_answers,
            "{}",
            test_case.description
        );
        remove_temp_tree(&root);
    }
}

#[test]
fn given_external_path_when_observing_then_rejects_canonical_target() {
    let test_cases = [StatTestCase {
        description: "rejects canonical paths outside the repository",
        expected_answers: &[None],
    }];
    for test_case in test_cases {
        let root = write_temp_tree(&[], &[]);
        let outside = root
            .parent()
            .expect("temporary root has a parent")
            .join("outside.py");
        fs::write(&outside, "VALUE: int = 1\n").expect("outside fixture is writable");
        let queries = vec![RepositoryStatQuery {
            relative_path: PathBuf::from("../outside.py"),
            kind: RepositoryStatKind::Exists,
        }];

        let answers = observe_repository_stats(&root, &queries);

        let actual: Vec<Option<(&str, bool)>> = answers
            .iter()
            .map(|answer| {
                answer
                    .as_ref()
                    .map(|value| (value.dependency_path.as_str(), value.answer))
            })
            .collect();
        assert_eq!(
            actual, test_case.expected_answers,
            "{}",
            test_case.description
        );
        fs::remove_file(outside).expect("outside fixture is removable");
        remove_temp_tree(&root);
    }
}
