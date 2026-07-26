//! Domain-shape rule behavior over fixture repositories.

use crate::helpers;
use crate::test_types;

#[test]
fn given_domain_shape_fixtures_when_checking_then_reports_expected_codes() {
    let test_cases = [
        test_types::CheckRepoTestCase {
            description: "a leaf domain with a main entry reports nothing",
            repo_files: vec![
                test_types::RepoFile {
                    path: "crates/example/src/reading/main/read_value.rs".to_owned(),
                    contents: "pub fn read_value() -> usize {\n    1\n}\n".to_owned(),
                },
                test_types::RepoFile {
                    path: "crates/example/src/reading/_helpers/loading.rs".to_owned(),
                    contents: "pub(crate) fn load() -> usize {\n    1\n}\n".to_owned(),
                },
            ],
            expected_violation_codes: vec![],
        },
        test_types::CheckRepoTestCase {
            description: "a branch domain of named subdomains reports nothing",
            repo_files: vec![
                test_types::RepoFile {
                    path: "crates/example/src/reading/paper/main/read_paper.rs".to_owned(),
                    contents: "pub fn read_paper() -> usize {\n    1\n}\n".to_owned(),
                },
                test_types::RepoFile {
                    path: "crates/example/src/reading/screen/main/read_screen.rs".to_owned(),
                    contents: "pub fn read_screen() -> usize {\n    1\n}\n".to_owned(),
                },
            ],
            expected_violation_codes: vec![],
        },
        test_types::CheckRepoTestCase {
            description: "a domain mixing role content with a subdomain is reported",
            repo_files: vec![
                test_types::RepoFile {
                    path: "crates/example/src/reading/main/read_value.rs".to_owned(),
                    contents: "pub fn read_value() -> usize {\n    1\n}\n".to_owned(),
                },
                test_types::RepoFile {
                    path: "crates/example/src/reading/screen/main/read_screen.rs".to_owned(),
                    contents: "pub fn read_screen() -> usize {\n    1\n}\n".to_owned(),
                },
            ],
            expected_violation_codes: vec!["RSR306"],
        },
        test_types::CheckRepoTestCase {
            description: "an ad hoc module at domain position is reported",
            repo_files: vec![
                test_types::RepoFile {
                    path: "crates/example/src/reading/main/read_value.rs".to_owned(),
                    contents: "pub fn read_value() -> usize {\n    1\n}\n".to_owned(),
                },
                test_types::RepoFile {
                    path: "crates/example/src/reading/loading.rs".to_owned(),
                    contents: "pub(crate) fn load() -> usize {\n    1\n}\n".to_owned(),
                },
            ],
            expected_violation_codes: vec!["RSR307"],
        },
        test_types::CheckRepoTestCase {
            description: "a role file at domain position is accepted",
            repo_files: vec![
                test_types::RepoFile {
                    path: "crates/example/src/reading/main/read_value.rs".to_owned(),
                    contents: "pub fn read_value() -> usize {\n    1\n}\n".to_owned(),
                },
                test_types::RepoFile {
                    path: "crates/example/src/reading/constants.rs".to_owned(),
                    contents: "pub(crate) const LIMIT: usize = 1;\n".to_owned(),
                },
            ],
            expected_violation_codes: vec![],
        },
        test_types::CheckRepoTestCase {
            description: "a leaf domain without a main entry is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/_helpers/loading.rs".to_owned(),
                contents: "pub(crate) fn load() -> usize {\n    1\n}\n".to_owned(),
            }],
            expected_violation_codes: vec!["RSR309"],
        },
        test_types::CheckRepoTestCase {
            description: "a leaf subdomain without a main entry is reported",
            repo_files: vec![
                test_types::RepoFile {
                    path: "crates/example/src/reading/paper/main/read_paper.rs".to_owned(),
                    contents: "pub fn read_paper() -> usize {\n    1\n}\n".to_owned(),
                },
                test_types::RepoFile {
                    path: "crates/example/src/reading/screen/_helpers/loading.rs".to_owned(),
                    contents: "pub(crate) fn load() -> usize {\n    1\n}\n".to_owned(),
                },
            ],
            expected_violation_codes: vec!["RSR309"],
        },
        test_types::CheckRepoTestCase {
            description: "a passive leaf domain holding only models is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/models.rs".to_owned(),
                contents:
                    "#[derive(Debug)]\npub(crate) struct Row {\n    pub(crate) id: usize,\n}\n"
                        .to_owned(),
            }],
            expected_violation_codes: vec!["RSR309"],
        },
        test_types::CheckRepoTestCase {
            description: "a feature subpackage inside a subdomain is reported",
            repo_files: vec![
                test_types::RepoFile {
                    path: "crates/example/src/reading/screen/main/read_screen.rs".to_owned(),
                    contents: "pub fn read_screen() -> usize {\n    1\n}\n".to_owned(),
                },
                test_types::RepoFile {
                    path: "crates/example/src/reading/screen/parsing/tokens.rs".to_owned(),
                    contents: "pub(crate) fn tokens() -> usize {\n    1\n}\n".to_owned(),
                },
            ],
            expected_violation_codes: vec!["RSR305", "RSR304"],
        },
        test_types::CheckRepoTestCase {
            description: "a nested module under a role container is accepted",
            repo_files: vec![
                test_types::RepoFile {
                    path: "crates/example/src/reading/screen/main/read_screen.rs".to_owned(),
                    contents: "pub fn read_screen() -> usize {\n    1\n}\n".to_owned(),
                },
                test_types::RepoFile {
                    path: "crates/example/src/reading/screen/_helpers/parsing/tokens.rs".to_owned(),
                    contents: "pub(crate) fn tokens() -> usize {\n    1\n}\n".to_owned(),
                },
            ],
            expected_violation_codes: vec![],
        },
    ];

    for test_case in test_cases {
        let repo_root = helpers::write_temp_repo_verbatim(&test_case);
        let actual_codes = helpers::collect_violation_codes(&repo_root);
        helpers::remove_temp_repo(&repo_root);
        assert_eq!(
            actual_codes, test_case.expected_violation_codes,
            "case failed: {}",
            test_case.description
        );
    }
}
