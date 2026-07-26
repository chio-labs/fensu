//! Test shape rule behavior over fixture repositories.

use crate::helpers;
use crate::test_types;

#[test]
fn given_test_shape_fixtures_when_checking_then_reports_expected_codes() {
    let test_cases = [
        test_types::CheckRepoTestCase {
            description: "compliant topic file reports nothing",
            repo_files: vec![
                test_types::RepoFile {
                    path: "crates/example/src/rules/mod.rs".to_owned(),
                    contents: String::new(),
                },
                test_types::RepoFile {
                path: "crates/example/tests/rules/test_checking.rs".to_owned(),
                contents: "use crate::test_types;\n\n#[test]\nfn given_a_when_b_then_c() {\n    let test_cases = [test_types::ValueTestCase { description: \"d\", expected_value: 1 }];\n\n    for test_case in &test_cases {\n        assert_eq!(1, test_case.expected_value, \"{}\", test_case.description);\n    }\n}\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec![],
        },
        test_types::CheckRepoTestCase {
            description: "test name outside the contract is reported",
            repo_files: vec![
                test_types::RepoFile {
                    path: "crates/example/src/rules/mod.rs".to_owned(),
                    contents: String::new(),
                },
                test_types::RepoFile {
                path: "crates/example/tests/rules/test_checking.rs".to_owned(),
                contents: "use crate::test_types;\n\n#[test]\nfn checks_reading() {\n    let test_cases = [test_types::ValueTestCase { description: \"d\", expected_value: 1 }];\n\n    for test_case in &test_cases {\n        assert_eq!(1, test_case.expected_value, \"{}\", test_case.description);\n    }\n}\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec!["RST302"],
        },
        test_types::CheckRepoTestCase {
            description: "branch inside a test is reported",
            repo_files: vec![
                test_types::RepoFile {
                    path: "crates/example/src/rules/mod.rs".to_owned(),
                    contents: String::new(),
                },
                test_types::RepoFile {
                path: "crates/example/tests/rules/test_checking.rs".to_owned(),
                contents: "use crate::test_types;\n\n#[test]\nfn given_a_when_b_then_c() {\n    let test_cases = [test_types::ValueTestCase { description: \"d\", expected_value: 1 }];\n\n    for test_case in &test_cases {\n        if test_case.expected_value > 0 {\n            assert_eq!(1, test_case.expected_value, \"{}\", test_case.description);\n        }\n    }\n}\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec!["RST104"],
        },
        test_types::CheckRepoTestCase {
            description: "test without case-driven shape reports every gap",
            repo_files: vec![
                test_types::RepoFile {
                    path: "crates/example/src/rules/mod.rs".to_owned(),
                    contents: String::new(),
                },
                test_types::RepoFile {
                path: "crates/example/tests/rules/test_checking.rs".to_owned(),
                contents: "#[test]\nfn given_a_when_b_then_c() {\n    assert_eq!(1, 1, \"fixed\");\n}\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec![
                "RST401", "RST404", "RST405", "RST407", "RST414", "RST420",
            ],
        },
        test_types::CheckRepoTestCase {
            description: "empty case array is reported",
            repo_files: vec![
                test_types::RepoFile {
                    path: "crates/example/src/rules/mod.rs".to_owned(),
                    contents: String::new(),
                },
                test_types::RepoFile {
                path: "crates/example/tests/rules/test_checking.rs".to_owned(),
                contents: "use crate::test_types;\n\n#[test]\nfn given_a_when_b_then_c() {\n    let test_cases: [test_types::ValueTestCase; 0] = [];\n\n    for test_case in &test_cases {\n        assert_eq!(1, test_case.expected_value, \"{}\", test_case.description);\n    }\n}\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec!["RST411"],
        },
        test_types::CheckRepoTestCase {
            description: "case loop variable with another name is reported",
            repo_files: vec![
                test_types::RepoFile {
                    path: "crates/example/src/rules/mod.rs".to_owned(),
                    contents: String::new(),
                },
                test_types::RepoFile {
                path: "crates/example/tests/rules/test_checking.rs".to_owned(),
                contents: "use crate::test_types;\n\n#[test]\nfn given_a_when_b_then_c() {\n    let test_cases = [test_types::ValueTestCase { description: \"d\", expected_value: 1 }];\n\n    for case in &test_cases {\n        assert_eq!(1, case.expected_value, \"{}\", case.description);\n    }\n}\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec!["RST402", "RST406"],
        },
        test_types::CheckRepoTestCase {
            description: "case constructor must name a TestCase type",
            repo_files: vec![
                test_types::RepoFile {
                    path: "crates/example/src/rules/mod.rs".to_owned(),
                    contents: String::new(),
                },
                test_types::RepoFile {
                    path: "crates/example/tests/rules/test_checking.rs".to_owned(),
                    contents: "use crate::test_types;\n\n#[test]\nfn given_a_when_b_then_c() {\n    let test_cases = [test_types::Value { description: \"d\", expected_value: 1 }];\n\n    for test_case in &test_cases {\n        assert_eq!(1, test_case.expected_value, \"{}\", test_case.description);\n    }\n}\n"
                        .to_owned(),
                },
            ],
            expected_violation_codes: vec!["RST403"],
        },
        test_types::CheckRepoTestCase {
            description: "case values must use an inline array",
            repo_files: vec![
                test_types::RepoFile {
                    path: "crates/example/src/rules/mod.rs".to_owned(),
                    contents: String::new(),
                },
                test_types::RepoFile {
                    path: "crates/example/tests/rules/test_checking.rs".to_owned(),
                    contents: "#[test]\nfn given_a_when_b_then_c() {\n    let test_cases = make_cases();\n\n    for test_case in &test_cases {\n        assert_eq!(1, test_case.expected_value, \"{}\", test_case.description);\n    }\n}\n"
                        .to_owned(),
                },
            ],
            expected_violation_codes: vec!["RST408"],
        },
        test_types::CheckRepoTestCase {
            description: "tuple-style cases are reported",
            repo_files: vec![
                test_types::RepoFile {
                    path: "crates/example/src/rules/mod.rs".to_owned(),
                    contents: String::new(),
                },
                test_types::RepoFile {
                    path: "crates/example/tests/rules/test_checking.rs".to_owned(),
                    contents: "use crate::test_types;\n\n#[test]\nfn given_a_when_b_then_c() {\n    let test_cases = [test_types::ValueTestCase(\"d\", 1)];\n\n    for test_case in &test_cases {\n        assert_eq!(1, test_case.expected_value, \"{}\", test_case.description);\n    }\n}\n"
                        .to_owned(),
                },
            ],
            expected_violation_codes: vec!["RST412"],
        },
        test_types::CheckRepoTestCase {
            description: "external test case constructors are reported",
            repo_files: vec![
                test_types::RepoFile {
                    path: "crates/example/src/rules/mod.rs".to_owned(),
                    contents: String::new(),
                },
                test_types::RepoFile {
                    path: "crates/example/tests/rules/test_checking.rs".to_owned(),
                    contents: "#[test]\nfn given_a_when_b_then_c() {\n    let test_cases = [ExternalTestCase { description: \"d\", expected_value: 1 }];\n\n    for test_case in &test_cases {\n        assert_eq!(1, test_case.expected_value, \"{}\", test_case.description);\n    }\n}\n"
                        .to_owned(),
                },
            ],
            expected_violation_codes: vec!["RST413"],
        },
        test_types::CheckRepoTestCase {
            description: "assertions without expected fields are reported",
            repo_files: vec![
                test_types::RepoFile {
                    path: "crates/example/src/rules/mod.rs".to_owned(),
                    contents: String::new(),
                },
                test_types::RepoFile {
                path: "crates/example/tests/rules/test_checking.rs".to_owned(),
                contents: "use crate::test_types;\n\n#[test]\nfn given_a_when_b_then_c() {\n    let test_cases = [test_types::ValueTestCase { description: \"d\", expected_value: 1 }];\n\n    for test_case in &test_cases {\n        assert_eq!(1, 1, \"{}\", test_case.description);\n    }\n}\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec!["RST404"],
        },
        test_types::CheckRepoTestCase {
            description: "tests without assertions are reported",
            repo_files: vec![
                test_types::RepoFile {
                    path: "crates/example/src/rules/mod.rs".to_owned(),
                    contents: String::new(),
                },
                test_types::RepoFile {
                    path: "crates/example/tests/rules/test_checking.rs".to_owned(),
                    contents: "use crate::test_types;\n\n#[test]\nfn given_a_when_b_then_c() {\n    let test_cases = [test_types::ValueTestCase { description: \"d\", expected_value: 1 }];\n\n    for test_case in &test_cases {\n        consume(test_case.expected_value);\n    }\n}\n"
                        .to_owned(),
                },
            ],
            expected_violation_codes: vec!["RST404"],
        },
        test_types::CheckRepoTestCase {
            description: "assertions without the description are reported",
            repo_files: vec![
                test_types::RepoFile {
                    path: "crates/example/src/rules/mod.rs".to_owned(),
                    contents: String::new(),
                },
                test_types::RepoFile {
                path: "crates/example/tests/rules/test_checking.rs".to_owned(),
                contents: "use crate::test_types;\n\n#[test]\nfn given_a_when_b_then_c() {\n    let test_cases = [test_types::ValueTestCase { description: \"d\", expected_value: 1 }];\n\n    for test_case in &test_cases {\n        assert_eq!(1, test_case.expected_value);\n    }\n}\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec!["RST407", "RST414"],
        },
        test_types::CheckRepoTestCase {
            description: "two case executors are reported",
            repo_files: vec![
                test_types::RepoFile {
                    path: "crates/example/src/rules/mod.rs".to_owned(),
                    contents: String::new(),
                },
                test_types::RepoFile {
                path: "crates/example/tests/rules/test_checking.rs".to_owned(),
                contents: "use crate::test_types;\n\n#[test]\nfn given_a_when_b_then_c() {\n    let test_cases = [test_types::ValueTestCase { description: \"d\", expected_value: 1 }];\n\n    for test_case in &test_cases {\n        assert_eq!(1, test_case.expected_value, \"{}\", test_case.description);\n    }\n\n    for test_case in &test_cases {\n        assert_eq!(1, test_case.expected_value, \"{}\", test_case.description);\n    }\n}\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec!["RST420"],
        },
        test_types::CheckRepoTestCase {
            description: "branch inside a test helper is reported",
            repo_files: vec![
                test_types::RepoFile {
                    path: "crates/example/src/rules/mod.rs".to_owned(),
                    contents: String::new(),
                },
                test_types::RepoFile {
                path: "crates/example/tests/rules/helpers.rs".to_owned(),
                contents: "pub(crate) fn pick(flag: bool) -> usize {\n    if flag {\n        1\n    } else {\n        2\n    }\n}\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec!["RST104"],
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
