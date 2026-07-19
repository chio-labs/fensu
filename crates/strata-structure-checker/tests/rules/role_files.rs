//! Role-file content and placement rule behavior over fixture repositories.

use crate::helpers;
use crate::test_types;

#[test]
fn given_role_file_fixtures_when_checking_then_reports_expected_codes() {
    let test_cases = [
        test_types::CheckRepoTestCase {
            description: "function in models role is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/models.rs".to_owned(),
                contents: "#[derive(Debug)]\npub struct Thing {\n    pub value: usize,\n}\n\npub fn build() -> usize {\n    1\n}\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec!["RSR001"],
        },
        test_types::CheckRepoTestCase {
            description: "function in types role is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/types.rs".to_owned(),
                contents: "pub type Value = usize;\n\npub fn build() -> usize {\n    1\n}\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec!["RSR002"],
        },
        test_types::CheckRepoTestCase {
            description: "struct in constants role is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/constants.rs".to_owned(),
                contents: "pub struct Wrong;\n".to_owned(),
            }],
            expected_violation_codes: vec!["RSR003"],
        },
        test_types::CheckRepoTestCase {
            description: "function in errors role is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/errors.rs".to_owned(),
                contents: "pub fn build() -> usize {\n    1\n}\n".to_owned(),
            }],
            expected_violation_codes: vec!["RSR004"],
        },
        test_types::CheckRepoTestCase {
            description: "public data struct outside models is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/helpers/carrying.rs".to_owned(),
                contents: "pub struct Carrier {\n    pub value: usize,\n}\n".to_owned(),
            }],
            expected_violation_codes: vec!["RSR101", "RSR205"],
        },
        test_types::CheckRepoTestCase {
            description: "public trait outside types is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/helpers/loading.rs".to_owned(),
                contents: "pub trait Loadable {\n    fn load(&self) -> usize;\n}\n".to_owned(),
            }],
            expected_violation_codes: vec!["RSR102", "RSR205"],
        },
        test_types::CheckRepoTestCase {
            description: "public constant outside constants is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/helpers/loading.rs".to_owned(),
                contents: "pub const LIMIT: usize = 3;\n".to_owned(),
            }],
            expected_violation_codes: vec!["RSR103", "RSR205"],
        },
        test_types::CheckRepoTestCase {
            description: "error type outside errors is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/helpers/parsing.rs".to_owned(),
                contents: "pub(crate) struct ParseError {\n    message: String,\n}\n".to_owned(),
            }],
            expected_violation_codes: vec!["RSR104"],
        },
        test_types::CheckRepoTestCase {
            description: "model without a Debug derive is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/models.rs".to_owned(),
                contents: "pub struct Thing {\n    pub value: usize,\n}\n".to_owned(),
            }],
            expected_violation_codes: vec!["RSS201"],
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
