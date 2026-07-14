//! Test layout rule behavior over fixture repositories.

use crate::helpers;
use crate::test_types;

#[test]
fn given_test_layout_fixtures_when_checking_then_reports_expected_codes() {
    let test_cases = [
        test_types::CheckRepoTestCase {
            description: "harness with implementation item is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/tests/rules.rs".to_owned(),
                contents: "fn support() -> usize {\n    1\n}\n".to_owned(),
            }],
            expected_violation_codes: vec!["RST101"],
        },
        test_types::CheckRepoTestCase {
            description: "harness module without a path attribute is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/tests/rules.rs".to_owned(),
                contents: "mod helpers;\n".to_owned(),
            }],
            expected_violation_codes: vec!["RST101"],
        },
        test_types::CheckRepoTestCase {
            description: "case struct without description field is reported",
            repo_files: vec![
                test_types::RepoFile {
                    path: "crates/example/src/rules/mod.rs".to_owned(),
                    contents: String::new(),
                },
                test_types::RepoFile {
                path: "crates/example/tests/rules/test_types.rs".to_owned(),
                contents: "pub(crate) struct ValueTestCase {\n    pub(crate) expected_value: usize,\n}\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec!["RST201"],
        },
        test_types::CheckRepoTestCase {
            description: "case struct without expected field is reported",
            repo_files: vec![
                test_types::RepoFile {
                    path: "crates/example/src/rules/mod.rs".to_owned(),
                    contents: String::new(),
                },
                test_types::RepoFile {
                path: "crates/example/tests/rules/test_types.rs".to_owned(),
                contents: "pub(crate) struct ValueTestCase {\n    pub(crate) description: &'static str,\n}\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec!["RST202"],
        },
        test_types::CheckRepoTestCase {
            description: "non-test function in a topic file is reported",
            repo_files: vec![
                test_types::RepoFile {
                    path: "crates/example/src/rules/mod.rs".to_owned(),
                    contents: String::new(),
                },
                test_types::RepoFile {
                path: "crates/example/tests/rules/checking.rs".to_owned(),
                contents: "use crate::test_types;\n\n#[test]\nfn given_a_when_b_then_c() {\n    let test_cases = [test_types::ValueTestCase { description: \"d\", expected_value: 1 }];\n\n    for test_case in &test_cases {\n        assert_eq!(1, test_case.expected_value, \"{}\", test_case.description);\n    }\n}\n\nfn support() -> usize {\n    1\n}\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec!["RST103"],
        },
        test_types::CheckRepoTestCase {
            description: "struct in a topic file is reported",
            repo_files: vec![
                test_types::RepoFile {
                    path: "crates/example/src/rules/mod.rs".to_owned(),
                    contents: String::new(),
                },
                test_types::RepoFile {
                path: "crates/example/tests/rules/checking.rs".to_owned(),
                contents: "struct Fixture {\n    value: usize,\n}\n".to_owned(),
            }],
            expected_violation_codes: vec!["RST203"],
        },
        test_types::CheckRepoTestCase {
            description: "module-level case array is reported",
            repo_files: vec![
                test_types::RepoFile {
                    path: "crates/example/src/rules/mod.rs".to_owned(),
                    contents: String::new(),
                },
                test_types::RepoFile {
                path: "crates/example/tests/rules/checking.rs".to_owned(),
                contents: "use crate::test_types;\n\nconst TEST_CASES: usize = 1;\n\n#[test]\nfn given_a_when_b_then_c() {\n    let test_cases = [test_types::ValueTestCase { description: \"d\", expected_value: 1 }];\n\n    for test_case in &test_cases {\n        assert_eq!(1, test_case.expected_value, \"{}\", test_case.description);\n    }\n}\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec!["RST401"],
        },
        test_types::CheckRepoTestCase {
            description: "constant declared after tests is reported",
            repo_files: vec![
                test_types::RepoFile {
                    path: "crates/example/src/rules/mod.rs".to_owned(),
                    contents: String::new(),
                },
                test_types::RepoFile {
                path: "crates/example/tests/rules/checking.rs".to_owned(),
                contents: "use crate::test_types;\n\n#[test]\nfn given_a_when_b_then_c() {\n    let test_cases = [test_types::ValueTestCase { description: \"d\", expected_value: 1 }];\n\n    for test_case in &test_cases {\n        assert_eq!(1, test_case.expected_value, \"{}\", test_case.description);\n    }\n}\n\nconst LIMIT: usize = 1;\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec!["RST105"],
        },
        test_types::CheckRepoTestCase {
            description: "test area without a source mirror is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/tests/unknown/checking.rs".to_owned(),
                contents: "use crate::test_types;\n\n#[test]\nfn given_a_when_b_then_c() {\n    let test_cases = [test_types::ValueTestCase { description: \"d\", expected_value: 1 }];\n\n    for test_case in &test_cases {\n        assert_eq!(1, test_case.expected_value, \"{}\", test_case.description);\n    }\n}\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec!["RST003"],
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
