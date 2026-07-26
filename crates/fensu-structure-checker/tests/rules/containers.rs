//! Container rule behavior over fixture repositories.

use crate::helpers;
use crate::test_types;

#[test]
fn given_container_fixtures_when_checking_then_reports_expected_codes() {
    let test_cases = [
        test_types::CheckRepoTestCase {
            description: "helpers container over the module budget is reported",
            repo_files: helpers::numbered_module_files(
                "crates/example/src/reading/helpers",
                11,
                "fn support() -> usize {\n    1\n}\n",
            ),
            expected_violation_codes: vec!["RSR301"],
        },
        test_types::CheckRepoTestCase {
            description: "helpers container mixing modules and buckets is reported",
            repo_files: vec![
                test_types::RepoFile {
                    path: "crates/example/src/reading/helpers/direct.rs".to_owned(),
                    contents: "fn support() -> usize {\n    1\n}\n".to_owned(),
                },
                test_types::RepoFile {
                    path: "crates/example/src/reading/helpers/grouping/inner.rs".to_owned(),
                    contents: "fn support() -> usize {\n    1\n}\n".to_owned(),
                },
            ],
            expected_violation_codes: vec!["RSR301"],
        },
        test_types::CheckRepoTestCase {
            description: "helpers bucket nesting beyond one level is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/helpers/grouping/inner/deep.rs".to_owned(),
                contents: "fn support() -> usize {\n    1\n}\n".to_owned(),
            }],
            expected_violation_codes: vec!["RSR301"],
        },
        test_types::CheckRepoTestCase {
            description: "main container over the entry budget is reported",
            repo_files: helpers::numbered_module_files(
                "crates/example/src/reading/main",
                21,
                "pub fn read_value() -> usize {\n    1\n}\n",
            ),
            expected_violation_codes: vec!["RSR302"],
        },
        test_types::CheckRepoTestCase {
            description: "implementation module outside role containers is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/scan.rs".to_owned(),
                contents: "fn scan() -> usize {\n    1\n}\n".to_owned(),
            }],
            expected_violation_codes: vec!["RSR304"],
        },
        test_types::CheckRepoTestCase {
            description: "entry module with two visible functions is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/main/read_value.rs".to_owned(),
                contents: "pub fn read_value() -> usize {\n    1\n}\n\npub fn read_other() -> usize {\n    2\n}\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec!["RSR401"],
        },
        test_types::CheckRepoTestCase {
            description: "entry module with a declaration item is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/main/read_value.rs".to_owned(),
                contents: "const LIMIT: usize = 1;\n\npub fn read_value() -> usize {\n    LIMIT\n}\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec!["RSR401"],
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

#[test]
fn given_helper_prefix_families_when_checking_then_reports_ungrouped_families() {
    let test_cases = [
        test_types::CheckRepoTestCase {
            description: "a helper prefix cluster at the threshold is reported",
            repo_files: vec![
                test_types::RepoFile {
                    path: "crates/example/src/alpha/helpers/memory_parsing.rs".to_owned(),
                    contents: String::new(),
                },
                test_types::RepoFile {
                    path: "crates/example/src/alpha/helpers/memory_values.rs".to_owned(),
                    contents: String::new(),
                },
                test_types::RepoFile {
                    path: "crates/example/src/alpha/helpers/memory_rendering.rs".to_owned(),
                    contents: String::new(),
                },
            ],
            expected_violation_codes: vec!["RSR308"],
        },
        test_types::CheckRepoTestCase {
            description: "a prefix pair below the cluster threshold is accepted",
            repo_files: vec![
                test_types::RepoFile {
                    path: "crates/example/src/alpha/helpers/load.rs".to_owned(),
                    contents: String::new(),
                },
                test_types::RepoFile {
                    path: "crates/example/src/alpha/helpers/load_optional.rs".to_owned(),
                    contents: String::new(),
                },
            ],
            expected_violation_codes: vec![],
        },
        test_types::CheckRepoTestCase {
            description: "a prefix family already grouped into a bucket is accepted",
            repo_files: vec![
                test_types::RepoFile {
                    path: "crates/example/src/alpha/helpers/memory/parsing.rs".to_owned(),
                    contents: String::new(),
                },
                test_types::RepoFile {
                    path: "crates/example/src/alpha/helpers/memory/values.rs".to_owned(),
                    contents: String::new(),
                },
            ],
            expected_violation_codes: vec![],
        },
        test_types::CheckRepoTestCase {
            description: "verb-prefixed entry modules in main are not a family",
            repo_files: vec![
                test_types::RepoFile {
                    path: "crates/example/src/alpha/main/extract_first.rs".to_owned(),
                    contents: "pub(crate) fn extract_first() {}\n".to_owned(),
                },
                test_types::RepoFile {
                    path: "crates/example/src/alpha/main/extract_second.rs".to_owned(),
                    contents: "pub(crate) fn extract_second() {}\n".to_owned(),
                },
            ],
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
