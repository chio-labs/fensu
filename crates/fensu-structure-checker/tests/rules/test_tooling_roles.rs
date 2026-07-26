//! Tooling-crate role policy over fixture repositories.

use crate::helpers;
use crate::test_types;

#[test]
fn given_tooling_role_fixtures_when_checking_then_reports_expected_codes() {
    let test_cases = [
        test_types::CheckRepoTestCase {
            description: "checker rules use explicit role boundaries",
            repo_files: vec![
                helpers::tooling_entry("rules", "check"),
                test_types::RepoFile {
                    path: "crates/fensu-structure-checker/src/rules/_helpers/policy.rs".to_owned(),
                    contents: "fn policy() -> usize {\n    1\n}\n".to_owned(),
                },
            ],
            expected_violation_codes: vec![],
        },
        test_types::CheckRepoTestCase {
            description: "direct rules implementation bypasses role boundaries",
            repo_files: vec![
                helpers::tooling_entry("rules", "check"),
                test_types::RepoFile {
                    path: "crates/fensu-structure-checker/src/rules/policy.rs".to_owned(),
                    contents: "fn policy() -> usize {\n    1\n}\n".to_owned(),
                },
            ],
            expected_violation_codes: vec!["RSR307", "RSR704", "RSR705"],
        },
        test_types::CheckRepoTestCase {
            description: "tooling root direct implementation module is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/fensu-structure-checker/src/runner.rs".to_owned(),
                contents: "fn run() -> usize {\n    1\n}\n".to_owned(),
            }],
            expected_violation_codes: vec!["RSR705"],
        },
        test_types::CheckRepoTestCase {
            description: "rule-code module filename is reported",
            repo_files: vec![
                helpers::tooling_entry("rules", "check"),
                test_types::RepoFile {
                    path: "crates/fensu-structure-checker/src/rules/_helpers/rsr706.rs".to_owned(),
                    contents: "fn policy() -> usize {\n    1\n}\n".to_owned(),
                },
            ],
            expected_violation_codes: vec!["RSR706"],
        },
        test_types::CheckRepoTestCase {
            description: "src bin adapter without main delegation is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/fensu-structure-checker/src/bin/report.rs".to_owned(),
                contents: "fn main() {}\n".to_owned(),
            }],
            expected_violation_codes: vec!["RSR702"],
        },
    ];

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
