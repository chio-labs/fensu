//! Hygiene rule behavior over fixture repositories.

use crate::helpers;
use crate::test_types;

#[test]
fn given_hygiene_fixtures_when_checking_then_reports_expected_codes() {
    let test_cases = [
        test_types::CheckRepoTestCase {
            description: "empty repository reports nothing",
            repo_files: vec![],
            expected_violation_codes: vec![],
        },
        test_types::CheckRepoTestCase {
            description: "standalone comment in library code is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/main/read_value.rs".to_owned(),
                contents: "// explains the obvious\npub fn read_value() -> usize {\n    1\n}\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec!["RSH002"],
        },
        test_types::CheckRepoTestCase {
            description: "multi-line doc comment is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/main/read_value.rs".to_owned(),
                contents: "/// Reads one value.\n/// It really does.\npub fn read_value() -> usize {\n    1\n}\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec!["RSH001"],
        },
        test_types::CheckRepoTestCase {
            description: "panic macro in library code is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/main/read_value.rs".to_owned(),
                contents: "pub fn read_value() -> usize {\n    panic!(\"boom\")\n}\n".to_owned(),
            }],
            expected_violation_codes: vec!["RSH003"],
        },
        test_types::CheckRepoTestCase {
            description: "assert macro in library code is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/main/read_value.rs".to_owned(),
                contents: "pub fn read_value(value: usize) -> usize {\n    assert!(value > 0);\n    value\n}\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec!["RSH004"],
        },
        test_types::CheckRepoTestCase {
            description: "unwrap and expect in library code are reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/main/read_value.rs".to_owned(),
                contents: "pub fn read_value(value: Option<usize>) -> usize {\n    value.unwrap().max(value.expect(\"present\"))\n}\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec!["RSH010", "RSH010"],
        },
        test_types::CheckRepoTestCase {
            description: "stdio macro outside the bin adapter is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/main/read_value.rs".to_owned(),
                contents: "pub fn read_value() -> usize {\n    println!(\"reading\");\n    1\n}\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec!["RSH011"],
        },
        test_types::CheckRepoTestCase {
            description: "stdio macro inside the bin adapter is allowed",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/main.rs".to_owned(),
                contents: "fn main() {\n    println!(\"ok\");\n}\n".to_owned(),
            }],
            expected_violation_codes: vec![],
        },
        test_types::CheckRepoTestCase {
            description: "crate root without forbid unsafe is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/lib.rs".to_owned(),
                contents: "pub mod reading;\n".to_owned(),
            }],
            expected_violation_codes: vec!["RSH012"],
        },
        test_types::CheckRepoTestCase {
            description: "unwrap in test code is reported",
            repo_files: vec![
                test_types::RepoFile {
                    path: "crates/example/src/rules/mod.rs".to_owned(),
                    contents: String::new(),
                },
                test_types::RepoFile {
                    path: "crates/example/tests/rules/checking.rs".to_owned(),
                    contents: "use crate::test_types;\n\n#[test]\nfn given_a_when_b_then_c() {\n    let test_cases = [test_types::ValueTestCase { description: \"d\", expected_value: 1 }];\n\n    for test_case in &test_cases {\n        let value = Some(test_case.expected_value).unwrap();\n        assert_eq!(value, test_case.expected_value, \"{}\", test_case.description);\n    }\n}\n"
                        .to_owned(),
                },
            ],
            expected_violation_codes: vec!["RSH010"],
        },
        test_types::CheckRepoTestCase {
            description: "string literal comparison is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/main/read_value.rs".to_owned(),
                contents: "pub fn read_value(kind: &str) -> usize {\n    let matched = kind == \"duckdb\";\n    usize::from(matched)\n}\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec!["RSH007"],
        },
        test_types::CheckRepoTestCase {
            description: "magic number comparison is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/main/read_value.rs".to_owned(),
                contents: "pub fn read_value(value: usize) -> usize {\n    let flag = value > 42;\n    usize::from(flag)\n}\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec!["RSH008"],
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
