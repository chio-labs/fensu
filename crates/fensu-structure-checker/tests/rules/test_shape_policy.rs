//! Adapted Rust function-shape behavior over fixture repositories.

use crate::helpers;
use crate::test_types;

#[test]
fn given_rust_shape_policy_fixtures_when_checking_then_reports_expected_codes() {
    let test_cases = [
        test_types::CheckRepoTestCase {
            description: "a main entry discarding a project must-use result is reported",
            repo_files: vec![
                test_types::RepoFile {
                    path: "crates/example/src/reading/_helpers/phase.rs".to_owned(),
                    contents: "#[must_use]\npub(crate) fn phase() -> usize {\n    1\n}\n"
                        .to_owned(),
                },
                test_types::RepoFile {
                    path: "crates/example/src/reading/main/read_value.rs".to_owned(),
                    contents: "pub fn read_value() -> usize {\n    crate::reading::_helpers::phase::phase();\n    1\n}\n"
                        .to_owned(),
                },
            ],
            expected_violation_codes: vec!["RSS101"],
        },
        test_types::CheckRepoTestCase {
            description: "an explicit discard of a project must-use result is accepted",
            repo_files: vec![
                test_types::RepoFile {
                    path: "crates/example/src/reading/_helpers/phase.rs".to_owned(),
                    contents: "#[must_use]\npub(crate) fn phase() -> usize {\n    1\n}\n"
                        .to_owned(),
                },
                test_types::RepoFile {
                    path: "crates/example/src/reading/main/read_value.rs".to_owned(),
                    contents: "pub fn read_value() -> usize {\n    let _ = crate::reading::_helpers::phase::phase();\n    1\n}\n"
                        .to_owned(),
                },
            ],
            expected_violation_codes: vec![],
        },
        test_types::CheckRepoTestCase {
            description: "a helper mutating through a returned mutable reference is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/_helpers/updating.rs".to_owned(),
                contents: "pub(crate) fn update(value: &mut usize) -> &mut usize {\n    *value += 1;\n    value\n}\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec!["RSS102"],
        },
        test_types::CheckRepoTestCase {
            description: "a mutable reference not returned is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/main/update_value.rs".to_owned(),
                contents: "pub fn update_value(value: &mut usize) {\n    *value += 1;\n}\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec!["RSS110"],
        },
        test_types::CheckRepoTestCase {
            description: "a returned mutable reference outside helpers is accepted",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/main/update_value.rs".to_owned(),
                contents: "pub fn update_value(value: &mut usize) -> &mut usize {\n    *value += 1;\n    value\n}\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec![],
        },
        test_types::CheckRepoTestCase {
            description: "a signature beyond the positional threshold is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/main/read_value.rs".to_owned(),
                contents: "pub fn read_value(one: usize, two: usize, three: usize, four: usize, five: usize) -> usize {\n    one + two + three + four + five\n}\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec!["RSS120"],
        },
        test_types::CheckRepoTestCase {
            description: "one named parameter struct is accepted",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/_helpers/calculation.rs".to_owned(),
                contents: "struct Calculation {\n    one: usize,\n    two: usize,\n    three: usize,\n    four: usize,\n    five: usize,\n}\n\npub(crate) fn calculate(request: Calculation) -> usize {\n    request.one + request.two + request.three + request.four + request.five\n}\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec![],
        },
        test_types::CheckRepoTestCase {
            description: "static interior mutation is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/_helpers/sequencing.rs".to_owned(),
                contents: "use std::sync::atomic::{AtomicUsize, Ordering};\n\nstatic SEQUENCE: AtomicUsize = AtomicUsize::new(0);\n\npub(crate) fn next() -> usize {\n    SEQUENCE.fetch_add(1, Ordering::Relaxed)\n}\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec!["RSS130"],
        },
        test_types::CheckRepoTestCase {
            description: "a nested iterator closure is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/_helpers/flattening.rs".to_owned(),
                contents: "pub(crate) fn flatten(values: &[Vec<usize>]) -> Vec<usize> {\n    values.iter().flat_map(|items| items.iter().map(|item| *item)).collect()\n}\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec!["RSS131"],
        },
        test_types::CheckRepoTestCase {
            description: "a single iterator closure is accepted",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/_helpers/doubling.rs".to_owned(),
                contents: "pub(crate) fn double(values: &[usize]) -> Vec<usize> {\n    values.iter().map(|value| value * 2).collect()\n}\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec![],
        },
    ];

    for test_case in test_cases {
        let repo_root = helpers::write_temp_repo(&test_case);
        let actual_codes = helpers::collect_violation_codes(&repo_root);
        helpers::remove_temp_repo(&repo_root);
        assert_eq!(
            actual_codes, test_case.expected_violation_codes,
            "case failed: {}",
            test_case.description
        );
    }
}

#[test]
fn given_nested_iterator_in_checker_when_checking_then_reports_tooling_code() {
    let test_cases = [test_types::CheckRepoTestCase {
        description: "nested iterator closure in checker tooling",
        repo_files: vec![
            test_types::RepoFile {
                path: "crates/fensu-structure-checker/src/checking/main/check.rs".to_owned(),
                contents: "pub fn check() -> usize {\n    1\n}\n".to_owned(),
            },
            test_types::RepoFile {
                path: "crates/fensu-structure-checker/src/checking/_helpers/flattening.rs".to_owned(),
                contents: "pub(crate) fn flatten(values: &[Vec<usize>]) -> Vec<usize> {\n    values.iter().flat_map(|items| items.iter().map(|item| *item)).collect()\n}\n"
                    .to_owned(),
            },
        ],
        expected_violation_codes: vec!["RSH006"],
    }];

    for test_case in &test_cases {
        let repo_root = helpers::write_tooling_temp_repo(test_case);
        let actual_codes = helpers::collect_violation_codes(&repo_root);
        helpers::remove_temp_repo(&repo_root);
        assert_eq!(
            actual_codes, test_case.expected_violation_codes,
            "case failed: {}",
            test_case.description
        );
    }
}
