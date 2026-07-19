//! Shared repository observation-index behavior.

use std::fs;

use strata_facts::snapshot::main::build_repository_observation_index::build_repository_observation_index;
use strata_facts::snapshot::models::RepositoryObservationAnswer;

use crate::helpers::{
    observation_paths, observation_query, owned_strings, remove_temp_tree, write_temp_tree,
};
use crate::test_types::{
    FixtureFile, GlobObservationTestCase, MissingObservationTestCase, ObservationTestCase,
};

#[test]
fn given_repository_queries_when_building_index_then_preserves_all_answers_and_order() {
    let test_cases = [ObservationTestCase {
        description: "answers source, stat, directory, anchor, and recursive glob queries",
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
            observation_query("pkg/source.py", "source", None, false),
            observation_query("pkg/source.py", "is_file", None, false),
            observation_query("pkg", "is_dir", None, false),
            observation_query("pkg/missing.py", "exists", None, false),
            observation_query("pkg", "directory_entries", None, false),
            observation_query("pkg", "python_anchor", None, false),
            observation_query("pkg", "glob", Some("*.py"), true),
        ];

        let index = build_repository_observation_index(&root, &queries)
            .expect("repository index is supported");
        let answers = queries
            .iter()
            .map(|query| query.observe(&index).expect("query is supported"))
            .collect::<Vec<_>>();

        assert_eq!(
            answers[0].answer,
            RepositoryObservationAnswer::String(test_case.expected_source_hash.to_owned()),
            "{}",
            test_case.description
        );
        assert_eq!(answers[1].answer, RepositoryObservationAnswer::Bool(true));
        assert_eq!(answers[2].answer, RepositoryObservationAnswer::Bool(true));
        assert_eq!(answers[3].answer, RepositoryObservationAnswer::Bool(false));
        let mut entries = observation_paths(&answers[4]);
        entries.sort();
        assert_eq!(
            entries,
            owned_strings(test_case.expected_directory_entries),
            "{}",
            test_case.description
        );
        let observed_order = fs::read_dir(root.join("pkg"))
            .expect("fixture directory is readable")
            .map(|entry| {
                format!(
                    "pkg/{}",
                    entry
                        .expect("fixture entry is readable")
                        .file_name()
                        .to_string_lossy()
                )
            })
            .collect::<Vec<_>>();
        assert_eq!(observation_paths(&answers[4]), observed_order);
        assert_eq!(
            observation_paths(&answers[5]),
            vec![test_case.expected_anchor]
        );
        let mut expected_recursive = observation_paths(&answers[4])
            .into_iter()
            .filter(|path| path.ends_with(".py"))
            .collect::<Vec<_>>();
        expected_recursive.push("pkg/deep/beta.py".to_owned());
        assert_eq!(
            observation_paths(&answers[6]),
            expected_recursive,
            "{}",
            test_case.description
        );
        remove_temp_tree(&root);
    }
}

#[test]
fn given_arbitrary_nested_glob_when_observing_then_matches_pathlib_order_without_duplicates() {
    let test_cases = [GlobObservationTestCase {
        description: "arbitrary nested matches follow pathlib starting-directory order",
        expected_match_count: 2,
    }];
    for test_case in test_cases {
        let root = write_temp_tree(
            &[
                FixtureFile {
                    path: "assets/alpha/nested/first.sql",
                    contents: "",
                },
                FixtureFile {
                    path: "assets/bravo/nested/second.sql",
                    contents: "",
                },
                FixtureFile {
                    path: "assets/bravo/ignored.py",
                    contents: "",
                },
            ],
            &[],
        );
        let queries = vec![
            observation_query("assets", "glob", Some("nested/*.sql"), true),
            observation_query("assets/alpha", "directory_entries", None, false),
        ];
        let index = build_repository_observation_index(&root, &queries)
            .expect("repository index is supported");
        let answer = queries[0].observe(&index).expect("glob is supported");
        let expected = fs::read_dir(root.join("assets"))
            .expect("assets fixture is readable")
            .filter_map(Result::ok)
            .map(|entry| entry.path().join("nested"))
            .filter_map(|directory| fs::read_dir(directory).ok())
            .flatten()
            .filter_map(Result::ok)
            .map(|entry| {
                entry
                    .path()
                    .strip_prefix(&root)
                    .expect("fixture stays below root")
                    .to_string_lossy()
                    .into_owned()
            })
            .collect::<Vec<_>>();

        assert_eq!(
            observation_paths(&answer).len(),
            test_case.expected_match_count,
            "{}",
            test_case.description
        );
        assert_eq!(
            observation_paths(&answer),
            expected,
            "{}",
            test_case.description
        );
        remove_temp_tree(&root);
    }
}

#[test]
fn given_missing_and_external_paths_when_rebuilding_index_then_is_conservative() {
    let test_cases = [MissingObservationTestCase {
        description: "missing paths turn current while external canonical targets stay rejected",
        expected_initial: false,
        expected_current: true,
        expected_external_supported: false,
    }];
    for test_case in test_cases {
        let root = write_temp_tree(&[], &[]);
        let missing = observation_query("dependency.py", "exists", None, false);
        let external = observation_query("../outside.py", "exists", None, false);
        let initial =
            build_repository_observation_index(&root, &[missing.clone(), external.clone()])
                .expect("repository index is supported");
        assert_eq!(
            missing
                .observe(&initial)
                .expect("missing query is supported")
                .answer,
            RepositoryObservationAnswer::Bool(test_case.expected_initial),
            "{}",
            test_case.description
        );
        assert_eq!(
            external.observe(&initial).is_some(),
            test_case.expected_external_supported,
            "{}",
            test_case.description
        );
        fs::write(root.join("dependency.py"), "VALUE: int = 1\n")
            .expect("dependency fixture is writable");
        let current = build_repository_observation_index(&root, std::slice::from_ref(&missing))
            .expect("repository index is supported");

        assert_eq!(
            missing
                .observe(&current)
                .expect("existing query is supported")
                .answer,
            RepositoryObservationAnswer::Bool(test_case.expected_current),
            "{}",
            test_case.description
        );
        remove_temp_tree(&root);
    }
}
