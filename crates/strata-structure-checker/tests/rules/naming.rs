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
            description: "honored contracts report nothing",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/helpers/loading.rs".to_owned(),
                contents: "fn is_ready(value: usize) -> bool {\n    value > 0\n}\n\nfn validate_input(value: usize) -> Result<(), String> {\n    let _ = value;\n    Ok(())\n}\n"
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
