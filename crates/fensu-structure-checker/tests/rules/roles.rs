//! Role rule behavior over fixture repositories.

use crate::helpers;
use crate::test_types;

#[test]
fn given_role_fixtures_when_checking_then_reports_expected_codes() {
    let test_cases = [
        test_types::CheckRepoTestCase {
            description: "compliant crate layout reports nothing",
            repo_files: vec![
                test_types::RepoFile {
                    path: "crates/example/src/lib.rs".to_owned(),
                    contents: "//! Example crate.\n#![forbid(unsafe_code)]\n\npub mod models;\n"
                        .to_owned(),
                },
                test_types::RepoFile {
                    path: "crates/example/src/models.rs".to_owned(),
                    contents: "//! Data models.\n\n#[derive(Debug)]\npub struct Thing {\n    pub value: usize,\n}\n"
                        .to_owned(),
                },
                test_types::RepoFile {
                    path: "crates/example/src/reading/helpers/loading.rs".to_owned(),
                    contents: "pub(super) fn load() -> usize {\n    1\n}\n".to_owned(),
                },
            ],
            expected_violation_codes: vec![],
        },
        test_types::CheckRepoTestCase {
            description: "banned generic filename is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/main/utils.rs".to_owned(),
                contents: "pub fn read_value() -> usize {\n    1\n}\n".to_owned(),
            }],
            expected_violation_codes: vec!["RSR201"],
        },
        test_types::CheckRepoTestCase {
            description: "helpers file instead of helpers directory is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/helpers.rs".to_owned(),
                contents: "fn support() -> usize {\n    1\n}\n".to_owned(),
            }],
            expected_violation_codes: vec!["RSR202", "RSR304"],
        },
        test_types::CheckRepoTestCase {
            description: "banned generic directory is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/common/loading.rs".to_owned(),
                contents: "fn load() -> usize {\n    1\n}\n".to_owned(),
            }],
            expected_violation_codes: vec!["RSR204", "RSR304"],
        },
        test_types::CheckRepoTestCase {
            description: "fully public item in helpers is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/helpers/loading.rs".to_owned(),
                contents: "pub fn load() -> usize {\n    1\n}\n".to_owned(),
            }],
            expected_violation_codes: vec!["RSR205"],
        },
        test_types::CheckRepoTestCase {
            description: "main module inside helpers is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/helpers/main.rs".to_owned(),
                contents: "fn orchestrate() -> usize {\n    1\n}\n".to_owned(),
            }],
            expected_violation_codes: vec!["RSR502"],
        },
        test_types::CheckRepoTestCase {
            description: "implementation item in mod file is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/mod.rs".to_owned(),
                contents: "pub mod loading;\n\npub fn read() -> usize {\n    1\n}\n".to_owned(),
            }],
            expected_violation_codes: vec!["RSR402"],
        },
        test_types::CheckRepoTestCase {
            description: "implementation item in crate root is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/lib.rs".to_owned(),
                contents: "#![forbid(unsafe_code)]\npub fn read() -> usize {\n    1\n}\n".to_owned(),
            }],
            expected_violation_codes: vec!["RSR406"],
        },
        test_types::CheckRepoTestCase {
            description: "scoped pub use re-export is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/main/read_value.rs".to_owned(),
                contents: "pub(crate) use std::collections::HashMap;\n\npub fn read_value(map: HashMap<usize, usize>) -> usize {\n    map.len()\n}\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec!["RSR403"],
        },
        test_types::CheckRepoTestCase {
            description: "pub use outside the crate root is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/main/read_value.rs".to_owned(),
                contents: "pub use std::collections::HashMap;\n\npub fn read_value() -> usize {\n    1\n}\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec!["RSR403"],
        },
        test_types::CheckRepoTestCase {
            description: "oversized file is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/models.rs".to_owned(),
                contents: "//! Data models.\n\n#[derive(Debug)]\npub struct Big {\n".to_owned()
                    + &"    pub value: usize,\n".repeat(400)
                    + "}\n",
            }],
            expected_violation_codes: vec!["RSR601"],
        },
        test_types::CheckRepoTestCase {
            description: "inline module body is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/mod.rs".to_owned(),
                contents: "mod inner {\n    fn read() -> usize {\n        1\n    }\n}\n".to_owned(),
            }],
            expected_violation_codes: vec!["RST001"],
        },
        test_types::CheckRepoTestCase {
            description: "bin adapter with extra functions is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/main.rs".to_owned(),
                contents: "fn main() {\n    support();\n}\n\nfn support() {}\n".to_owned(),
            }],
            expected_violation_codes: vec!["RSR701"],
        },
        test_types::CheckRepoTestCase {
            description: "constant declared after functions is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/helpers/loading.rs".to_owned(),
                contents: "fn support() -> usize {\n    1\n}\n\nconst LIMIT: usize = 2;\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec!["RSR503"],
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
