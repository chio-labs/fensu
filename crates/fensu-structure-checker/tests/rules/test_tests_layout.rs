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
            description: "test function outside a test scope is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/_helpers/test_checking.rs".to_owned(),
                contents: "#[test]\nfn misplaced_test() {}\n".to_owned(),
            }],
            expected_violation_codes: vec!["RST002"],
        },
        test_types::CheckRepoTestCase {
            description: "direct integration test lacks source-area depth",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/tests/test_checking.rs".to_owned(),
                contents: "#[test]\nfn given_a_when_b_then_c() {}\n".to_owned(),
            }],
            expected_violation_codes: vec!["RST004", "RST101"],
        },
        test_types::CheckRepoTestCase {
            description: "relative import in a test topic is reported",
            repo_files: vec![
                test_types::RepoFile {
                    path: "crates/example/src/rules/mod.rs".to_owned(),
                    contents: String::new(),
                },
                test_types::RepoFile {
                    path: "crates/example/tests/rules/test_checking.rs".to_owned(),
                    contents: "use super::helpers::value;\n".to_owned(),
                },
            ],
            expected_violation_codes: vec!["RSL001", "RST102"],
        },
        test_types::CheckRepoTestCase {
            description: "test topic without test prefix is reported",
            repo_files: vec![
                test_types::RepoFile {
                    path: "crates/example/src/rules/mod.rs".to_owned(),
                    contents: String::new(),
                },
                test_types::RepoFile {
                    path: "crates/example/tests/rules/checking.rs".to_owned(),
                    contents: String::new(),
                },
            ],
            expected_violation_codes: vec!["RST301"],
        },
        test_types::CheckRepoTestCase {
            description: "binary test without binary-area depth is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/tests/bin/test_report.rs".to_owned(),
                contents: String::new(),
            }],
            expected_violation_codes: vec!["RST007"],
        },
        test_types::CheckRepoTestCase {
            description: "binary test area without a Cargo binary is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/tests/bin/report/test_checking.rs".to_owned(),
                contents: String::new(),
            }],
            expected_violation_codes: vec!["RST008"],
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
                path: "crates/example/tests/rules/test_checking.rs".to_owned(),
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
                path: "crates/example/tests/rules/test_checking.rs".to_owned(),
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
                path: "crates/example/tests/rules/test_checking.rs".to_owned(),
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
                path: "crates/example/tests/rules/test_checking.rs".to_owned(),
                contents: "use crate::test_types;\n\n#[test]\nfn given_a_when_b_then_c() {\n    let test_cases = [test_types::ValueTestCase { description: \"d\", expected_value: 1 }];\n\n    for test_case in &test_cases {\n        assert_eq!(1, test_case.expected_value, \"{}\", test_case.description);\n    }\n}\n\nconst LIMIT: usize = 1;\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec!["RST105"],
        },
        test_types::CheckRepoTestCase {
            description: "test area without a source mirror is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/tests/unknown/test_checking.rs".to_owned(),
                contents: "use crate::test_types;\n\n#[test]\nfn given_a_when_b_then_c() {\n    let test_cases = [test_types::ValueTestCase { description: \"d\", expected_value: 1 }];\n\n    for test_case in &test_cases {\n        assert_eq!(1, test_case.expected_value, \"{}\", test_case.description);\n    }\n}\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec!["RST003", "RST006"],
        },
        test_types::CheckRepoTestCase {
            description: "private source unit-test tree uses test structure rules",
            repo_files: vec![
                test_types::RepoFile {
                    path: "crates/example/src/cache/mod.rs".to_owned(),
                    contents: "#[cfg(test)]\nmod tests;\n".to_owned(),
                },
                test_types::RepoFile {
                    path: "crates/example/src/cache/tests.rs".to_owned(),
                    contents: "#[path = \"tests/test_checking.rs\"]\nmod checking;\n#[path = \"tests/test_types.rs\"]\nmod test_types;\n".to_owned(),
                },
                test_types::RepoFile {
                    path: "crates/example/src/cache/tests/test_types.rs".to_owned(),
                    contents: "pub(crate) struct ValueTestCase {\n    pub(crate) description: &'static str,\n    pub(crate) expected_value: usize,\n}\n".to_owned(),
                },
                test_types::RepoFile {
                    path: "crates/example/src/cache/tests/test_checking.rs".to_owned(),
                    contents: "use crate::cache::tests::test_types;\n\n#[test]\nfn given_a_when_b_then_c() {\n    let test_cases = [test_types::ValueTestCase { description: \"d\", expected_value: 1 }];\n\n    for test_case in &test_cases {\n        assert_eq!(1, test_case.expected_value, \"{}\", test_case.description);\n    }\n}\n".to_owned(),
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

#[test]
fn given_missing_runtime_anchors_when_checking_then_reports_layout_codes() {
    let test_cases = [
        test_types::CheckRepoTestCase {
            description: "runtime tests require a library package anchor",
            repo_files: vec![
                test_types::RepoFile {
                    path: "crates/example/src/rules/mod.rs".to_owned(),
                    contents: String::new(),
                },
                test_types::RepoFile {
                    path: "crates/example/tests/rules/test_types.rs".to_owned(),
                    contents: String::new(),
                },
                test_types::RepoFile {
                    path: "crates/example/tests/rules/test_checking.rs".to_owned(),
                    contents: String::new(),
                },
            ],
            expected_violation_codes: vec!["RST005"],
        },
        test_types::CheckRepoTestCase {
            description: "test topics require local test types",
            repo_files: vec![
                test_types::RepoFile {
                    path: "crates/example/src/lib.rs".to_owned(),
                    contents: "#![forbid(unsafe_code)]\n".to_owned(),
                },
                test_types::RepoFile {
                    path: "crates/example/src/rules/mod.rs".to_owned(),
                    contents: String::new(),
                },
                test_types::RepoFile {
                    path: "crates/example/tests/rules/test_checking.rs".to_owned(),
                    contents: String::new(),
                },
            ],
            expected_violation_codes: vec!["RST204"],
        },
    ];

    for test_case in &test_cases {
        let repo_root = helpers::write_temp_repo_verbatim(test_case);
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
fn given_harness_area_modules_when_checking_then_reports_undeclared_modules() {
    let test_cases = [
        test_types::CheckRepoTestCase {
            description: "a module never declared by any area file is reported",
            repo_files: vec![
                test_types::RepoFile {
                    path: "crates/example/tests/rules.rs".to_owned(),
                    contents: "#[path = \"rules/test_declared.rs\"]\nmod declared;\n#[path = \"rules/test_types.rs\"]\nmod test_types;\n".to_owned(),
                },
                test_types::RepoFile {
                    path: "crates/example/tests/rules/test_declared.rs".to_owned(),
                    contents: String::new(),
                },
                test_types::RepoFile {
                    path: "crates/example/tests/rules/test_orphaned.rs".to_owned(),
                    contents: String::new(),
                },
                test_types::RepoFile {
                    path: "crates/example/src/rules/mod.rs".to_owned(),
                    contents: String::new(),
                },
            ],
            expected_violation_codes: vec!["RST110"],
        },
        test_types::CheckRepoTestCase {
            description: "a module declared by a sibling area file is accepted",
            repo_files: vec![
                test_types::RepoFile {
                    path: "crates/example/tests/rules.rs".to_owned(),
                    contents: "#[path = \"rules/test_declared.rs\"]\nmod declared;\n#[path = \"rules/test_types.rs\"]\nmod test_types;\n".to_owned(),
                },
                test_types::RepoFile {
                    path: "crates/example/tests/rules/test_declared.rs".to_owned(),
                    contents: "#[path = \"test_nested.rs\"]\nmod nested;\n".to_owned(),
                },
                test_types::RepoFile {
                    path: "crates/example/tests/rules/test_nested.rs".to_owned(),
                    contents: String::new(),
                },
                test_types::RepoFile {
                    path: "crates/example/src/rules/mod.rs".to_owned(),
                    contents: String::new(),
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
            "{}",
            test_case.description
        );
    }
}
