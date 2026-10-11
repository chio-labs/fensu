//! Tuple budgets cover written type positions without inspecting macro tokens.

use crate::{helpers, test_types};
use fensu_rust::configuration::main::rule_options::resolve_rule_options;
use fensu_rust::rules::main::check_repository_with_config::check_repository_with_config;

#[test]
fn given_tuple_types_when_checking_then_only_wide_written_types_are_reported() {
    let test_cases = [
        test_types::TupleTestCase {
            description: "type alias",
            source: "type Value = (u8, u8, u8, u8);",
            max_tuple_arity: 3,
            expected_lines: &[1],
        },
        test_types::TupleTestCase {
            description: "tuple struct field",
            source: "struct Value((u8, u8, u8, u8));",
            max_tuple_arity: 3,
            expected_lines: &[1],
        },
        test_types::TupleTestCase {
            description: "tuple enum field",
            source: "enum Value { Item((u8, u8, u8, u8)) }",
            max_tuple_arity: 3,
            expected_lines: &[1],
        },
        test_types::TupleTestCase {
            description: "named struct and enum fields",
            source: "struct Value { data: (u8, u8, u8, u8) }\nenum Item { Value { data: (u8, u8, u8, u8) } }",
            max_tuple_arity: 3,
            expected_lines: &[1, 2],
        },
        test_types::TupleTestCase {
            description: "function input and output",
            source: "fn value(data: (u8, u8, u8, u8)) -> (u8, u8, u8, u8) { data }",
            max_tuple_arity: 3,
            expected_lines: &[1, 1],
        },
        test_types::TupleTestCase {
            description: "trait method input and output",
            source: "trait Value { fn value(&self, data: (u8, u8, u8, u8)) -> (u8, u8, u8, u8); }",
            max_tuple_arity: 3,
            expected_lines: &[1, 1],
        },
        test_types::TupleTestCase {
            description: "impl method input and output",
            source: "impl Value { fn value(&self, data: (u8, u8, u8, u8)) -> (u8, u8, u8, u8) { data } }",
            max_tuple_arity: 3,
            expected_lines: &[1, 1],
        },
        test_types::TupleTestCase {
            description: "let annotation",
            source: "fn value() { let data: (u8, u8, u8, u8) = (1, 2, 3, 4); }",
            max_tuple_arity: 3,
            expected_lines: &[1],
        },
        test_types::TupleTestCase {
            description: "closure input and output annotations",
            source: "fn value() { let function = |data: (u8, u8, u8, u8)| -> (u8, u8, u8, u8) { data }; }",
            max_tuple_arity: 3,
            expected_lines: &[1, 1],
        },
        test_types::TupleTestCase {
            description: "generic arguments and expression turbofish",
            source: "type Values = Vec<Option<(u8, u8, u8, u8)>>;\nfn value() { call::<(u8, u8, u8, u8)>(); }",
            max_tuple_arity: 3,
            expected_lines: &[1, 2],
        },
        test_types::TupleTestCase {
            description: "nested wide tuple and narrow parent",
            source: "type Value = (u8, (u8, u8, u8, u8));",
            max_tuple_arity: 3,
            expected_lines: &[1],
        },
        test_types::TupleTestCase {
            description: "nested wide tuples each report once",
            source: "type Value = (u8, u8, u8, (u8, u8, u8, u8));",
            max_tuple_arity: 3,
            expected_lines: &[1, 1],
        },
        test_types::TupleTestCase {
            description: "associated consts associated types and statics",
            source: "trait Value { const DATA: (u8, u8, u8, u8); }\nimpl Value for Item { const DATA: (u8, u8, u8, u8) = (1, 2, 3, 4); type Data = (u8, u8, u8, u8); }\nstatic DATA: (u8, u8, u8, u8) = (1, 2, 3, 4);",
            max_tuple_arity: 3,
            expected_lines: &[1, 2, 2, 3],
        },
        test_types::TupleTestCase {
            description: "expressions and patterns are not types",
            source: "fn value() { let (a, b, c, d) = (1, 2, 3, 4); match (a, b, c, d) { (1, 2, 3, 4) => (), _ => () } }",
            max_tuple_arity: 3,
            expected_lines: &[],
        },
        test_types::TupleTestCase {
            description: "unit one two and three element types",
            source: "type Value = ((), (u8,), (u8, u8)); type Other = (u8, u8, u8);",
            max_tuple_arity: 3,
            expected_lines: &[],
        },
        test_types::TupleTestCase {
            description: "macro definitions and invocations are opaque",
            source: "macro_rules! value { () => { type Value = (u8, u8, u8, u8); } }\nvalue!((u8, u8, u8, u8));",
            max_tuple_arity: 3,
            expected_lines: &[],
        },
        test_types::TupleTestCase {
            description: "configured higher arity permits four elements",
            source: "type Value = (u8, u8, u8, u8);",
            max_tuple_arity: 4,
            expected_lines: &[],
        },
        test_types::TupleTestCase {
            description: "configured lower arity still excludes unit",
            source: "type Unit = (); type Pair = (u8, u8);",
            max_tuple_arity: 1,
            expected_lines: &[1],
        },
    ];
    for test_case in test_cases {
        let fixture = test_types::CheckRepoTestCase {
            description: test_case.description,
            repo_files: vec![test_types::RepoFile {
                path: "crates/example/src/values/_helpers/value.rs".to_owned(),
                contents: test_case.source.to_owned(),
            }],
            expected_violation_codes: vec![],
        };
        let root = helpers::write_temp_repo(&fixture);
        let options: toml::Table = format!(
            "[FPRSS012]\nmax_tuple_arity = {}",
            test_case.max_tuple_arity
        )
        .parse()
        .expect("valid rule options");
        let config = resolve_rule_options((test_case.max_tuple_arity != 3).then_some(&options))
            .expect("tuple arity option is valid");
        let violations =
            check_repository_with_config(&root, &config).expect("valid repository policy");
        helpers::remove_temp_repo(&root);
        let lines: Vec<_> = violations
            .iter()
            .filter(|violation| violation.code == "RSS012")
            .map(|violation| violation.line.expect("tuple start line"))
            .collect();
        assert_eq!(lines, test_case.expected_lines, "{}", test_case.description);
    }
}
