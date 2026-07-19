//! Naming contract rule behavior over fixture repositories.

use crate::helpers;
use crate::test_types;

#[test]
fn given_naming_fixtures_when_checking_then_reports_expected_codes() {
    let test_cases = [
        test_types::CheckRepoTestCase {
            description: "validator returning a value is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/helpers/loading.rs".to_owned(),
                contents: "fn validate_input(value: usize) -> usize {\n    value\n}\n".to_owned(),
            }],
            expected_violation_codes: vec!["RSN001"],
        },
        test_types::CheckRepoTestCase {
            description: "predicate not returning bool is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/helpers/loading.rs".to_owned(),
                contents: "fn is_ready(value: usize) -> usize {\n    value\n}\n".to_owned(),
            }],
            expected_violation_codes: vec!["RSN002"],
        },
        test_types::CheckRepoTestCase {
            description: "converter returning nothing is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/helpers/loading.rs".to_owned(),
                contents: "fn to_display(value: usize) {\n    let _ = value;\n}\n".to_owned(),
            }],
            expected_violation_codes: vec!["RSN003"],
        },
        test_types::CheckRepoTestCase {
            description: "converter explicitly returning unit is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/helpers/loading.rs".to_owned(),
                contents: "fn to_display(value: usize) -> () {\n    let _ = value;\n}\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec!["RSN003"],
        },
        test_types::CheckRepoTestCase {
            description: "getter prefix is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/helpers/loading.rs".to_owned(),
                contents: "fn get_value() -> usize {\n    1\n}\n".to_owned(),
            }],
            expected_violation_codes: vec!["RSN003"],
        },
        test_types::CheckRepoTestCase {
            description: "iterator name without an iterator is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/helpers/loading.rs".to_owned(),
                contents: "fn iter_values() -> usize {\n    1\n}\n".to_owned(),
            }],
            expected_violation_codes: vec!["RSN004"],
        },
        test_types::CheckRepoTestCase {
            description: "result with unit error is not a validator result",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/helpers/loading.rs".to_owned(),
                contents: "fn validate_input() -> Result<String, ()> {\n    Ok(String::new())\n}\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec!["RSN001"],
        },
        test_types::CheckRepoTestCase {
            description: "trait predicate contract is checked",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/helpers/loading.rs".to_owned(),
                contents: "trait Readiness {\n    fn is_ready(&self) -> usize;\n}\n".to_owned(),
            }],
            expected_violation_codes: vec!["RSN002"],
        },
        test_types::CheckRepoTestCase {
            description: "honored contracts report nothing",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/helpers/loading.rs".to_owned(),
                contents: "fn is_ready(value: usize) -> bool {\n    value > 0\n}\n\nfn validate_input(value: usize) -> () {\n    let _ = value;\n}\n\nfn enforce_input() -> std::result::Result<(), Error> {\n    Ok(())\n}\n\nfn iter_values() -> impl Iterator<Item = usize> {\n    [1].into_iter()\n}\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec![],
        },
    ];

    for test_case in &test_cases {
        let repo_root = helpers::write_temp_repo(test_case);
        let actual_codes = helpers::collect_violation_codes(&repo_root);
        helpers::remove_temp_repo(&repo_root);

        assert_eq!(
            actual_codes, test_case.expected_violation_codes,
            "case failed: {}",
            test_case.description
        );
    }
}
