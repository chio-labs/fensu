//! Repository source and namespace observation behavior.

use std::fs;
use std::path::PathBuf;

use strata_facts::snapshot::main::observe_repository_contexts::observe_repository_contexts;
use strata_facts::snapshot::models::{RepositoryContextKind, RepositoryContextQuery};

use crate::helpers::{remove_temp_tree, write_temp_tree};
use crate::test_types::{ContextTestCase, FixtureFile};

#[test]
fn given_repository_tree_when_observing_contexts_then_returns_ordered_answers() {
    let test_cases = [ContextTestCase {
        description: "returns source identity, directory order, and the first Python anchor",
        expected_source_hash: "9e26bf369911c45c243c684147b23fc9e1dcfcf257d299a1c632016a6fcd33f4",
        expected_directory_entries: &["pkg/alpha.py", "pkg/deep", "pkg/source.py", "pkg/zeta.py"],
        expected_anchor: "pkg/alpha.py",
    }];
    for test_case in test_cases {
        let root = write_temp_tree(
            &[
                FixtureFile {
                    path: "pkg/source.py",
                    contents: "x = 1\n",
                },
                FixtureFile {
                    path: "pkg/zeta.py",
                    contents: "",
                },
                FixtureFile {
                    path: "pkg/alpha.py",
                    contents: "",
                },
                FixtureFile {
                    path: "pkg/deep/beta.py",
                    contents: "",
                },
            ],
            &[],
        );
        let queries = vec![
            RepositoryContextQuery {
                relative_path: PathBuf::from("pkg/source.py"),
                kind: RepositoryContextKind::Source,
            },
            RepositoryContextQuery {
                relative_path: PathBuf::from("pkg"),
                kind: RepositoryContextKind::DirectoryEntries,
            },
            RepositoryContextQuery {
                relative_path: PathBuf::from("pkg"),
                kind: RepositoryContextKind::PythonAnchor,
            },
        ];

        let answers = observe_repository_contexts(&root, &queries);

        let source = answers[0]
            .as_ref()
            .expect("source observation is supported");
        assert_eq!(
            source.source_answer.as_deref(),
            Some(test_case.expected_source_hash),
            "{}",
            test_case.description
        );
        let directory = answers[1]
            .as_ref()
            .expect("directory observation is supported");
        let mut sorted_entries = directory.path_answer.clone();
        sorted_entries.sort();
        assert_eq!(
            sorted_entries,
            test_case
                .expected_directory_entries
                .iter()
                .map(ToString::to_string)
                .collect::<Vec<_>>(),
            "{}",
            test_case.description
        );
        let observation_order: Vec<String> = fs::read_dir(root.join("pkg"))
            .expect("fixture directory is readable")
            .map(|entry| entry.expect("fixture entry is readable"))
            .map(|entry| format!("pkg/{}", entry.file_name().to_string_lossy()))
            .collect();
        assert_eq!(
            directory.path_answer, observation_order,
            "directory answers must preserve filesystem observation order; {}",
            test_case.description
        );
        let anchor = answers[2]
            .as_ref()
            .expect("anchor observation is supported");
        assert_eq!(
            anchor.path_answer.first().map(String::as_str),
            Some(test_case.expected_anchor),
            "{}",
            test_case.description
        );
        remove_temp_tree(&root);
    }
}
