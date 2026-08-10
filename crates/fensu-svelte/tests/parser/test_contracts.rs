//! Public parser and cache identity tests.

use fensu_svelte::{CACHE_CONTRACT_VERSION, PARSER_CONTRACT_VERSION, RECOVERY_NODE_KINDS};

use crate::test_types;

#[test]
fn given_native_parser_when_reading_contracts_then_versions_are_explicit() {
    let cli_analyzer_source = include_str!("../../../fensu-cli/src/analyzer.rs");
    let test_cases = [test_types::ContractTestCase {
        description: "owned facts and the CLI analyzer share one Svelte cache identity",
        expected_parser_contract: "svelte-backend-v11",
        expected_cache_contract: "svelte-backend-v11",
        expected_recovery_kinds: &[
            "attribute_expected_equals_tail",
            "attribute_sequence_recovery_tail",
            "erroneous_end_tag",
            "erroneous_end_tag_name",
            "incomplete_attribute_expression",
            "malformed_block",
            "orphan_branch",
            "tag_missing_whitespace_trailing",
        ],
        expected_cli_contract_fragment: "Self::Svelte => \"svelte-backend-v11\"",
    }];

    for test_case in &test_cases {
        assert_eq!(
            PARSER_CONTRACT_VERSION, test_case.expected_parser_contract,
            "{}",
            test_case.description
        );
        assert_eq!(
            CACHE_CONTRACT_VERSION, test_case.expected_cache_contract,
            "{}",
            test_case.description
        );
        assert_eq!(
            RECOVERY_NODE_KINDS, test_case.expected_recovery_kinds,
            "{}",
            test_case.description
        );
        assert!(
            cli_analyzer_source.contains(test_case.expected_cli_contract_fragment),
            "{}",
            test_case.description
        );
    }
}
