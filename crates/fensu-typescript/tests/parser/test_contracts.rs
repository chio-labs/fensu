//! Public parser and cache identity tests.

use fensu_typescript::{CACHE_CONTRACT_VERSION, PARSER_CONTRACT_VERSION};

use crate::test_types;

#[test]
fn given_native_parser_when_reading_contracts_then_versions_are_explicit() {
    let test_cases = [test_types::ContractTestCase {
        description: "TypeScript parser and fact cache identities advance together",
        expected_parser_contract: "typescript-backend-v11",
        expected_cache_contract: "typescript-backend-v11",
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
    }
}
