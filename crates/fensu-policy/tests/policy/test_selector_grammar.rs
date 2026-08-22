//! Public exact-code and selector grammar contract.

use crate::test_types::ValidationTestCase;
use fensu_policy::policy::main::rule_code_is_exact::rule_code_is_exact;
use fensu_policy::policy::main::rule_selector_is_valid::rule_selector_is_valid;
use fensu_policy::policy::models::ProductRuleCodeGrammar;
use fensu_policy::policy::types::RuleCodeGrammar;

#[test]
fn given_code_examples_when_validating_then_enforces_exact_ascii_grammar() {
    let test_cases = [
        ValidationTestCase {
            description: "core code",
            value: "FFA001",
            expected_valid: true,
        },
        ValidationTestCase {
            description: "short core code",
            value: "FFA01",
            expected_valid: false,
        },
        ValidationTestCase {
            description: "long core code",
            value: "FFA0001",
            expected_valid: false,
        },
        ValidationTestCase {
            description: "pack code",
            value: "FPDGA001",
            expected_valid: true,
        },
        ValidationTestCase {
            description: "pack without namespace",
            value: "FP123",
            expected_valid: false,
        },
        ValidationTestCase {
            description: "short custom code",
            value: "X1",
            expected_valid: true,
        },
        ValidationTestCase {
            description: "product custom code",
            value: "XSQBKD001",
            expected_valid: true,
        },
        ValidationTestCase {
            description: "custom code without digits",
            value: "XRT",
            expected_valid: false,
        },
        ValidationTestCase {
            description: "empty code",
            value: "",
            expected_valid: false,
        },
        ValidationTestCase {
            description: "lowercase code",
            value: "ffa001",
            expected_valid: false,
        },
        ValidationTestCase {
            description: "non ASCII code",
            value: "FFÄ001",
            expected_valid: false,
        },
    ];

    for test_case in test_cases {
        assert_eq!(
            rule_code_is_exact(test_case.value),
            test_case.expected_valid,
            "case failed: {}",
            test_case.description
        );
    }
}

#[test]
fn given_selector_examples_when_validating_then_allows_valid_prefixes() {
    let test_cases = [
        ValidationTestCase {
            description: "core root",
            value: "FF",
            expected_valid: true,
        },
        ValidationTestCase {
            description: "core family",
            value: "FFA",
            expected_valid: true,
        },
        ValidationTestCase {
            description: "core digit prefix",
            value: "FFA0",
            expected_valid: true,
        },
        ValidationTestCase {
            description: "exact core",
            value: "FFA001",
            expected_valid: true,
        },
        ValidationTestCase {
            description: "long core",
            value: "FFA0001",
            expected_valid: false,
        },
        ValidationTestCase {
            description: "two core families",
            value: "FFRR",
            expected_valid: false,
        },
        ValidationTestCase {
            description: "pack root",
            value: "FP",
            expected_valid: true,
        },
        ValidationTestCase {
            description: "pack namespace",
            value: "FPDG",
            expected_valid: true,
        },
        ValidationTestCase {
            description: "numeric pack selector",
            value: "FP123",
            expected_valid: true,
        },
        ValidationTestCase {
            description: "custom root",
            value: "X",
            expected_valid: true,
        },
        ValidationTestCase {
            description: "product custom namespace",
            value: "XSQBK",
            expected_valid: true,
        },
        ValidationTestCase {
            description: "exact custom",
            value: "XSQBKD001",
            expected_valid: true,
        },
        ValidationTestCase {
            description: "letter after digit",
            value: "X1A",
            expected_valid: false,
        },
        ValidationTestCase {
            description: "empty selector",
            value: "",
            expected_valid: false,
        },
        ValidationTestCase {
            description: "lowercase selector",
            value: "x",
            expected_valid: false,
        },
    ];

    for test_case in test_cases {
        assert_eq!(
            rule_selector_is_valid(test_case.value),
            test_case.expected_valid,
            "case failed: {}",
            test_case.description
        );
    }
}

#[test]
fn given_product_grammar_examples_when_validating_then_enforces_namespaces_without_panicking() {
    let grammar =
        ProductRuleCodeGrammar::new("SQBK", "XSQBK").expect("SQLBuild namespaces are valid");
    let test_cases = [
        ValidationTestCase {
            description: "built-in code",
            value: "SQBKJ001",
            expected_valid: true,
        },
        ValidationTestCase {
            description: "custom code",
            value: "XSQBKD001",
            expected_valid: true,
        },
        ValidationTestCase {
            description: "non-ASCII built-in code",
            value: "SQBKÄ00",
            expected_valid: false,
        },
        ValidationTestCase {
            description: "non-ASCII custom code",
            value: "XSQBKÄ00",
            expected_valid: false,
        },
    ];

    for test_case in test_cases {
        assert_eq!(
            grammar.rule_code_is_exact(test_case.value),
            test_case.expected_valid,
            "case failed: {}",
            test_case.description
        );
    }
    assert!(!grammar.rule_selector_is_valid("SQBKÄ"));
    assert!(!grammar.rule_selector_is_valid("XSQBKÄ"));
}
