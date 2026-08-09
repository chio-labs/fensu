//! Exhaustive authored metadata rendering contracts for core rules.

use crate::analyzer::AnalyzerId;
use crate::catalogue::_helpers::loading::rule_catalogue;
use crate::catalogue::_helpers::policy::RulePolicy;
use crate::catalogue::_helpers::rendering::render;
use crate::models::Config;
use crate::skills::_helpers::context::selection;
use crate::tests::test_types::{
    AnalyzerCatalogueTestCase, AnalyzerRenderingTestCase, CoreRuleRenderingTestCase,
};

#[test]
fn given_every_core_rule_when_rendering_then_complete_authored_metadata_is_visible() {
    let test_cases = [CoreRuleRenderingTestCase {
        description: "every native core registration renders the complete stable metadata frame",
        expected_core_count: 111,
        expected_labels: &[
            "Authored metadata:",
            "Family:",
            "Severity:",
            "Kind: core",
            "Pack: None",
            "Alias: None",
            "Analyzers: python",
            "Enabled by default:",
            "Execution owner:",
            "Cacheability:",
            "Source: core",
            "Message:",
            "Remediation:",
            "Loaded project policy:",
            "Selected:",
            "Blocking:",
            "Warning:",
            "Ignored:",
        ],
    }];
    for test_case in test_cases {
        let catalogue = rule_catalogue().expect("embedded catalogue");
        let core = catalogue
            .iter()
            .filter(|metadata| metadata.pack.is_none())
            .collect::<Vec<_>>();
        assert_eq!(
            core.len(),
            test_case.expected_core_count,
            "{}",
            test_case.description
        );
        for metadata in core {
            let output = render(
                metadata,
                &Config::default(),
                false,
                &RulePolicy {
                    selected: false,
                    blocking: false,
                    warning: false,
                    ignored: false,
                },
            );
            assert!(
                output.starts_with(&format!("{} {}\n", metadata.code, metadata.slug)),
                "{}: {}",
                test_case.description,
                metadata.code
            );
            assert!(
                test_case
                    .expected_labels
                    .iter()
                    .all(|label| output.contains(label)),
                "{}: {}\n{output}",
                test_case.description,
                metadata.code
            );
            assert!(
                !output.contains("\u{1b}"),
                "{}: {}",
                test_case.description,
                metadata.code
            );
            assert_eq!(metadata.analyzers, [AnalyzerId::Python]);
        }
    }
}

#[test]
fn given_python_catalogue_and_other_analyzer_when_selecting_then_applicability_precedes_selectors()
{
    let test_cases = [AnalyzerCatalogueTestCase {
        description: "broad catalogue view contains no Python rules for TypeScript",
        analyzer: AnalyzerId::TypeScript,
        select: &[],
        expected_codes: &[],
        expected_error: None,
    }];
    let root = tempfile::tempdir().expect("catalogue selection root");
    for test_case in &test_cases {
        let config = Config {
            analyzer: test_case.analyzer,
            select: test_case
                .select
                .iter()
                .map(|value| (*value).to_owned())
                .collect(),
            ..Config::default()
        };
        let selected =
            selection::selection(&config, root.path()).expect("applicable catalogue selection");
        assert_eq!(test_case.expected_error, None, "{}", test_case.description);
        assert_eq!(
            selected
                .catalogue
                .iter()
                .map(|rule| rule.code.as_str())
                .collect::<Vec<_>>(),
            test_case.expected_codes,
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_incompatible_python_selector_when_selecting_then_error_names_analyzer() {
    let test_cases = [
        AnalyzerCatalogueTestCase {
            description: "broad Python selector is incompatible with TypeScript",
            analyzer: AnalyzerId::TypeScript,
            select: &["FFA"],
            expected_codes: &[],
            expected_error: Some(
                "selector FFA, but matching rules are not applicable to analyzer typescript",
            ),
        },
        AnalyzerCatalogueTestCase {
            description: "exact Python rule is incompatible with Svelte",
            analyzer: AnalyzerId::Svelte,
            select: &["FFA001"],
            expected_codes: &[],
            expected_error: Some(
                "rule FFA001, but matching rules are not applicable to analyzer svelte",
            ),
        },
    ];
    let root = tempfile::tempdir().expect("catalogue selection root");
    for test_case in &test_cases {
        let config = Config {
            analyzer: test_case.analyzer,
            select: test_case
                .select
                .iter()
                .map(|value| (*value).to_owned())
                .collect(),
            ..Config::default()
        };
        let error =
            selection::selection(&config, root.path()).expect_err("incompatible exact rule");
        assert!(
            error.contains(test_case.expected_error.unwrap_or_default()),
            "{}",
            test_case.description
        );
        assert!(
            test_case.expected_codes.is_empty(),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_incompatible_alias_when_selecting_then_alias_fails_closed() {
    let test_cases = [AnalyzerCatalogueTestCase {
        description: "exact Dagster alias is incompatible with TypeScript",
        analyzer: AnalyzerId::TypeScript,
        select: &[],
        expected_codes: &[],
        expected_error: Some("matching rules are not applicable to analyzer typescript"),
    }];
    let root = tempfile::tempdir().expect("catalogue selection root");
    let alias = rule_catalogue()
        .expect("embedded catalogue")
        .iter()
        .find(|rule| rule.alias_of.is_some())
        .expect("catalogue has an alias");
    for test_case in &test_cases {
        let config = Config {
            analyzer: test_case.analyzer,
            rule_packs: vec![alias.pack.clone().unwrap_or_default()],
            select: vec![alias.code.clone()],
            ..Config::default()
        };
        let error = selection::selection(&config, root.path()).expect_err("incompatible alias");
        assert!(
            error.contains(test_case.expected_error.unwrap_or_default()),
            "{}",
            test_case.description
        );
        assert!(
            test_case.expected_codes.is_empty(),
            "{}",
            test_case.description
        );
        assert!(test_case.select.is_empty(), "{}", test_case.description);
    }
}

#[test]
fn given_unsorted_analyzer_applicability_when_rendering_then_metadata_is_deterministic() {
    let test_cases = [AnalyzerRenderingTestCase {
        description: "rendered analyzer applicability is sorted",
        expected_line: "Analyzers: python, svelte, typescript\n",
    }];
    let mut metadata = rule_catalogue().expect("embedded catalogue")[0].clone();
    metadata.analyzers = vec![
        AnalyzerId::TypeScript,
        AnalyzerId::Python,
        AnalyzerId::Svelte,
    ];
    for test_case in &test_cases {
        let output = render(
            &metadata,
            &Config::default(),
            false,
            &RulePolicy {
                selected: false,
                blocking: false,
                warning: false,
                ignored: false,
            },
        );
        assert!(
            output.contains(test_case.expected_line),
            "{}",
            test_case.description
        );
    }
}
