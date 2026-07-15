//! Ordered direct and recursive Python glob behavior.

use std::path::PathBuf;

use strata_facts::snapshot::main::observe_python_globs::observe_python_globs;
use strata_facts::snapshot::models::RepositoryPythonGlobQuery;

use crate::helpers::{remove_temp_tree, write_temp_tree};
use crate::test_types::{FixtureFile, GlobTestCase};

#[test]
fn given_python_tree_when_globbing_then_preserves_query_and_path_order() {
    let test_cases = [GlobTestCase {
        description: "returns direct and recursive Python paths in filesystem iteration order",
        expected_direct_paths: &["pkg/first.py"],
        expected_recursive_paths: &[
            "pkg/first.py",
            "pkg/main/__init__.py",
            "pkg/_helpers/promote/helper.py",
        ],
    }];
    for test_case in test_cases {
        let root = write_temp_tree(
            &[
                FixtureFile {
                    path: "pkg/first.py",
                    contents: "",
                },
                FixtureFile {
                    path: "pkg/readme.txt",
                    contents: "",
                },
                FixtureFile {
                    path: "pkg/_helpers/promote/helper.py",
                    contents: "",
                },
                FixtureFile {
                    path: "pkg/main/__init__.py",
                    contents: "",
                },
            ],
            &[],
        );
        let queries = vec![
            RepositoryPythonGlobQuery {
                relative_path: PathBuf::from("pkg"),
                recursive: false,
            },
            RepositoryPythonGlobQuery {
                relative_path: PathBuf::from("pkg"),
                recursive: true,
            },
        ];

        let answers = observe_python_globs(&root, &queries);

        let actual_direct = answers[0].as_ref().map(|answer| answer.answer.clone());
        assert_eq!(
            actual_direct,
            Some(
                test_case
                    .expected_direct_paths
                    .iter()
                    .map(ToString::to_string)
                    .collect()
            ),
            "{}",
            test_case.description
        );
        let actual_recursive = answers[1].as_ref().map(|answer| answer.answer.clone());
        assert_eq!(
            actual_recursive,
            Some(
                test_case
                    .expected_recursive_paths
                    .iter()
                    .map(ToString::to_string)
                    .collect()
            ),
            "{}",
            test_case.description
        );
        remove_temp_tree(&root);
    }
}
