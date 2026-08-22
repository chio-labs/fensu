//! Shared implementation identity validation.

use crate::test_types::{ImplementationIdentityTestCase, SqlDialect, SqlRule};
use fensu_policy::policy::errors::PolicyError;
use fensu_policy::policy::main::validate_unique_implementations::validate_unique_implementations;

#[test]
fn given_aliases_for_one_implementation_when_validating_then_rejects_duplicate_identity() {
    let test_cases = [ImplementationIdentityTestCase {
        description: "two display codes share one implementation",
        rules: vec![
            SqlRule {
                code: "XSQBKD001",
                enabled: true,
                dialects: &[SqlDialect::Postgres],
                implementation: Some("XSQBKD001"),
            },
            SqlRule {
                code: "XSQBKD099",
                enabled: true,
                dialects: &[SqlDialect::Postgres],
                implementation: Some("XSQBKD001"),
            },
        ],
        expected_error: PolicyError::DuplicateImplementation {
            first_code: "XSQBKD001".to_owned(),
            second_code: "XSQBKD099".to_owned(),
            implementation_code: "XSQBKD001".to_owned(),
        },
    }];

    for test_case in test_cases {
        let rules = test_case.rules.iter().collect::<Vec<_>>();
        let error = validate_unique_implementations(&rules)
            .expect_err("duplicate implementation must fail");
        assert_eq!(
            error, test_case.expected_error,
            "case failed: {}",
            test_case.description
        );
    }
}
