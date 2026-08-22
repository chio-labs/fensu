//! Applicability-aware selector validation failures.

use crate::test_types::{SelectorValidationTestCase, SqlDialect, SqlPolicyTestCase, SqlRule};
use fensu_policy::policy::errors::PolicyError;
use fensu_policy::policy::main::resolve_policy::resolve_policy;
use fensu_policy::policy::main::validate_selector_group::validate_selector_group;
use fensu_policy::policy::models::{PolicyCatalogues, PolicySelectors, ProductRuleCodeGrammar};

#[test]
fn given_invalid_or_unmatched_selectors_when_validating_then_returns_typed_errors() {
    let rules = [SqlRule {
        code: "XSQBKD001",
        enabled: true,
        dialects: &[SqlDialect::Postgres],
        implementation: None,
    }];
    let configured = [&rules[0]];
    let applicable = [&rules[0]];
    let catalogues = PolicyCatalogues {
        configured: &configured,
        applicable: &applicable,
    };
    let grammar =
        ProductRuleCodeGrammar::new("SQBK", "XSQBK").expect("SQLBuild namespaces are valid");
    let test_cases = [
        SelectorValidationTestCase {
            description: "lowercase selector",
            selector: "xsqbk",
            expected_error: PolicyError::InvalidSelector {
                group: "select".to_owned(),
                selector: "xsqbk".to_owned(),
            },
        },
        SelectorValidationTestCase {
            description: "unmatched selector",
            selector: "SQBKA",
            expected_error: PolicyError::SelectorMatchesNoConfiguredRule {
                group: "select".to_owned(),
                selector: "SQBKA".to_owned(),
            },
        },
    ];

    for test_case in test_cases {
        let error = validate_selector_group(
            "select",
            &[test_case.selector.to_owned()],
            &catalogues,
            &grammar,
        )
        .expect_err("selector must fail");
        assert_eq!(
            error, test_case.expected_error,
            "case failed: {}",
            test_case.description
        );
    }
}

#[test]
fn given_only_inapplicable_match_when_resolving_then_distinguishes_exact_selector() {
    let test_cases = [SqlPolicyTestCase {
        description: "exact selector matches only a Snowflake rule",
        rules: vec![SqlRule {
            code: "XSQBKD001",
            enabled: true,
            dialects: &[SqlDialect::Snowflake],
            implementation: None,
        }],
        dialect: SqlDialect::Postgres,
        selectors: PolicySelectors {
            select: vec!["XSQBKD001".to_owned()],
            warn: Vec::new(),
            ignore: Vec::new(),
        },
        expected_catalogue: Vec::new(),
        expected_blocking: Vec::new(),
        expected_warnings: Vec::new(),
        expected_ignored: Vec::new(),
        expected_error: Some(PolicyError::SelectorMatchesOnlyInapplicableRules {
            group: "select".to_owned(),
            selector: "XSQBKD001".to_owned(),
            exact: true,
        }),
    }];

    for test_case in test_cases {
        let catalogue = test_case.rules.iter().collect::<Vec<_>>();
        let grammar =
            ProductRuleCodeGrammar::new("SQBK", "XSQBK").expect("SQLBuild namespaces are valid");
        let error = resolve_policy(
            &catalogue,
            &test_case.dialect,
            &test_case.selectors,
            &grammar,
        )
        .expect_err("inapplicable selector must fail");
        assert_eq!(
            Some(error),
            test_case.expected_error,
            "case failed: {}",
            test_case.description
        );
    }
}
