use std::str::FromStr;

use crate::analyzer::AnalyzerId;
use crate::tests::test_types::AnalyzerContractTestCase;

#[test]
fn given_analyzer_spelling_when_resolving_identity_then_contract_is_typed_and_case_sensitive() {
    let test_cases = [
        AnalyzerContractTestCase {
            description: "Python is available",
            value: "python",
            expected_analyzer: Some(AnalyzerId::Python),
            expected_backend_error: None,
            expected_display: Some("python"),
            expected_cache_contract: Some("python-ruff-py312-v1"),
        },
        AnalyzerContractTestCase {
            description: "TypeScript is known but unavailable",
            value: "typescript",
            expected_analyzer: Some(AnalyzerId::TypeScript),
            expected_backend_error: Some("Known analyzer backend unavailable: typescript."),
            expected_display: Some("typescript"),
            expected_cache_contract: Some("typescript-backend-v1"),
        },
        AnalyzerContractTestCase {
            description: "Svelte is known but unavailable",
            value: "svelte",
            expected_analyzer: Some(AnalyzerId::Svelte),
            expected_backend_error: Some("Known analyzer backend unavailable: svelte."),
            expected_display: Some("svelte"),
            expected_cache_contract: Some("svelte-backend-v1"),
        },
        AnalyzerContractTestCase {
            description: "case variants remain unknown",
            value: "TypeScript",
            expected_analyzer: None,
            expected_backend_error: None,
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
        let backend_error = parsed.and_then(|analyzer| analyzer.require_backend().err());
        assert_eq!(
            backend_error.as_deref(),
            test_case.expected_backend_error,
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
