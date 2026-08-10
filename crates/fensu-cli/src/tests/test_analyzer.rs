use std::str::FromStr;

use crate::analyzer::AnalyzerId;
use crate::tests::test_types::{AnalyzerContractTestCase, ParserContractTestCase};

#[test]
fn given_analyzer_spelling_when_resolving_identity_then_contract_is_typed_and_case_sensitive() {
    let test_cases = [
        AnalyzerContractTestCase {
            description: "Python is available",
            value: "python",
            expected_analyzer: Some(AnalyzerId::Python),
            expected_display: Some("python"),
            expected_cache_contract: Some("python-ruff-py312-v1"),
        },
        AnalyzerContractTestCase {
            description: "TypeScript is publicly available",
            value: "typescript",
            expected_analyzer: Some(AnalyzerId::TypeScript),
            expected_display: Some("typescript"),
            expected_cache_contract: Some("typescript-policy-v4"),
        },
        AnalyzerContractTestCase {
            description: "Svelte is publicly available",
            value: "svelte",
            expected_analyzer: Some(AnalyzerId::Svelte),
            expected_display: Some("svelte"),
            expected_cache_contract: Some("svelte-policy-v4"),
        },
        AnalyzerContractTestCase {
            description: "case variants remain unknown",
            value: "TypeScript",
            expected_analyzer: None,
            expected_display: None,
            expected_cache_contract: None,
        },
    ];
    for test_case in &test_cases {
        let parsed = AnalyzerId::from_str(test_case.value).ok();
        assert_eq!(
            parsed, test_case.expected_analyzer,
            "{}",
            test_case.description
        );
        assert_eq!(
            parsed.map(|analyzer| analyzer.to_string()).as_deref(),
            test_case.expected_display,
            "{}",
            test_case.description
        );
        assert_eq!(
            parsed.map(AnalyzerId::cache_contract),
            test_case.expected_cache_contract,
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_web_analyzer_when_reading_parser_contract_then_it_matches_owned_parser_crate() {
    let test_cases = [
        ParserContractTestCase {
            description: "TypeScript contract comes from the owned parser",
            analyzer: AnalyzerId::TypeScript,
            expected_contract: fensu_typescript::PARSER_CONTRACT_VERSION,
        },
        ParserContractTestCase {
            description: "Svelte contract comes from the owned parser",
            analyzer: AnalyzerId::Svelte,
            expected_contract: fensu_svelte::PARSER_CONTRACT_VERSION,
        },
    ];
    for test_case in &test_cases {
        assert_eq!(
            test_case.analyzer.parser_contract(),
            test_case.expected_contract,
            "{}",
            test_case.description
        );
    }
}
