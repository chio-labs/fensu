//! Direct native core-rule diagnostic contracts.

use std::collections::HashMap;

use fensu_facts::extension::models::ProgramHandle;
use fensu_native::rules::main::evaluate_core_rules::evaluate_core_rules;
use fensu_native::rules::models::{NativeProjectPlane, NativeRuleContext};
use ruff_python_ast::PythonVersion;

use crate::test_types;

#[test]
fn given_core_rule_contract_corpus_when_evaluating_then_diagnostics_are_exact() {
    let test_cases = [test_types::CoreRuleCorpusTestCase {
        description: "legacy captured requests preserve every proven core diagnostic",
        expected_fixture_count: 531,
        expected_core_code_count: 111,
        expected_non_faulting_codes: &["FFR707", "FFT001"],
    }];
    for test_case in &test_cases {
        assert_eq!(
            crate::helpers::fixtures().len(),
            test_case.expected_fixture_count,
            "{}",
            test_case.description
        );
        crate::helpers::assert_corpus_contract(test_case, crate::helpers::fixtures());
    }
}

#[test]
fn given_generated_core_rule_corpus_when_evaluating_then_every_registration_is_covered() {
    let test_cases = [test_types::CoreRuleCorpusTestCase {
        description: "current rule suites reproducibly cover every core registration",
        expected_fixture_count: 132,
        expected_core_code_count: 111,
        expected_non_faulting_codes: &["FFR301", "FFR302", "FFR306", "FFR308", "FFR309"],
    }];
    for test_case in &test_cases {
        assert_eq!(
            crate::helpers::generated_fixtures().len(),
            test_case.expected_fixture_count,
            "{}",
            test_case.description
        );
        crate::helpers::assert_corpus_contract(test_case, crate::helpers::generated_fixtures());
    }
}

#[test]
fn given_undeclared_native_option_when_evaluating_then_value_is_rejected_not_ignored() {
    let test_cases = [test_types::NativeOptionRejectionTestCase {
        description: "undeclared native option is transported and rejected",
        code: "FFA001",
        option_name: "mode",
        option_value: "\"strict\"",
        expected_error_fragment: "does not declare option mode",
        expected_stored_value: "\"strict\"",
    }];
    for test_case in test_cases {
        let program = ProgramHandle::parse_many(
            vec!["def run(value):\n    return value\n".to_owned()],
            PythonVersion {
                major: 3,
                minor: 12,
            },
        )
        .pop()
        .flatten()
        .expect("valid Python");
        let context = NativeRuleContext {
            rule_options: HashMap::from([(
                test_case.code.to_owned(),
                HashMap::from([(
                    test_case.option_name.to_owned(),
                    test_case.option_value.to_owned(),
                )]),
            )]),
            ..NativeRuleContext::default()
        };

        let error = evaluate_core_rules(
            &program,
            &[test_case.code.to_owned()],
            &context,
            &NativeProjectPlane::default(),
        )
        .expect_err("undeclared native option must fail");

        assert!(
            error.contains(test_case.expected_error_fragment),
            "{}",
            test_case.description
        );
        assert_eq!(
            context.option(test_case.code, test_case.option_name),
            Some(test_case.expected_stored_value),
            "{}",
            test_case.description
        );
    }
}
