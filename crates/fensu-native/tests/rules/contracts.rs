//! Direct native core-rule diagnostic contracts.

use crate::test_types;

#[test]
fn given_core_rule_contract_corpus_when_evaluating_then_diagnostics_are_exact() {
    let test_cases = [test_types::CoreRuleCorpusTestCase {
        description: "captured native requests preserve every proven core diagnostic",
        expected_fixture_count: 531,
    }];
    for test_case in test_cases {
        let fixtures = crate::helpers::fixtures();
        assert_eq!(
            fixtures.len(),
            test_case.expected_fixture_count,
            "{}",
            test_case.description
        );
        crate::helpers::run_fixtures(fixtures);
    }
}
