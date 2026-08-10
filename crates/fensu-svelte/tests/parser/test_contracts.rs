//! Public parser and cache identity tests.

use fensu_svelte::{CACHE_CONTRACT_VERSION, PARSER_CONTRACT_VERSION, RECOVERY_NODE_KINDS};

use crate::test_types;

#[test]
fn given_native_parser_when_reading_contracts_then_versions_are_explicit() {
    let test_cases = [test_types::ContractTestCase {
        description: "Svelte parser and fact cache identities advance together",
        expected_parser_contract: "svelte-backend-v12",
        expected_cache_contract: "svelte-backend-v12",
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
    }
}
