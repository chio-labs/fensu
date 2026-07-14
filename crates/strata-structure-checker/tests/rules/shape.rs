//! Shape rule behavior over fixture repositories.

use crate::helpers;
use crate::test_types;

#[test]
fn given_shape_fixtures_when_checking_then_reports_expected_codes() {
    let test_cases = [
        test_types::CheckRepoTestCase {
            description: "function over the parameter budget is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/helpers/loading.rs".to_owned(),
                contents: "fn support(a1: usize, a2: usize, a3: usize, a4: usize, a5: usize, a6: usize, a7: usize, a8: usize, a9: usize, a10: usize, a11: usize) -> usize {\n    a1\n}\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec!["RSS010"],
        },
        test_types::CheckRepoTestCase {
            description: "function over the global statement budget is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/helpers/loading.rs".to_owned(),
                contents: "fn support() -> usize {\n".to_owned()
                    + &"    let value = 1;\n".repeat(71)
                    + "    value\n}\n",
            }],
            expected_violation_codes: vec!["RSS011"],
        },
        test_types::CheckRepoTestCase {
            description: "entry over the entry statement budget is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/main/read_value.rs".to_owned(),
                contents: "pub fn read_value() -> usize {\n    let mut value = 1;\n".to_owned()
                    + &"    value += 1;\n".repeat(41)
                    + "    value\n}\n",
            }],
            expected_violation_codes: vec!["RSS001"],
        },
        test_types::CheckRepoTestCase {
            description: "entry coordinating too many callees is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/main/read_value.rs".to_owned(),
                contents: "pub fn read_value() -> usize {\n    let value = source();\n    value.m01().m02().m03().m04().m05().m06().m07().m08().m09().m10().m11().m12().m13().m14().m15().m16().m17().m18().m19().m20();\n    1\n}\n"
                    .to_owned(),
            }],
            expected_violation_codes: vec!["RSS002"],
        },
        test_types::CheckRepoTestCase {
            description: "entry juggling too many locals is reported",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/main/read_value.rs".to_owned(),
                contents: "pub fn read_value() -> usize {\n".to_owned()
                    + &"    let value = 1;\n".repeat(21)
                    + "    value\n}\n",
            }],
            expected_violation_codes: vec!["RSS003"],
        },
        test_types::CheckRepoTestCase {
            description: "closure body is not charged to its owning function",
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/reading/main/read_value.rs".to_owned(),
                contents: "pub fn read_value() -> usize {\n    let operation = || {\n".to_owned()
                    + &"        let value = 1;\n".repeat(35)
                    + "        value\n    };\n    operation()\n}\n",
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
