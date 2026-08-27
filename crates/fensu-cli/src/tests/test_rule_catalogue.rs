//! Exhaustive authored metadata rendering contracts for core rules.

use crate::analyzer::AnalyzerId;
use crate::catalogue::_helpers::loading::rule_catalogue;
use crate::catalogue::_helpers::policy::RulePolicy;
use crate::catalogue::_helpers::rendering::render;
use crate::models::Config;
use crate::skills::_helpers::context::selection;
use crate::tests::test_types::{
    AnalyzerCatalogueTestCase, AnalyzerRenderingTestCase, CoreRuleRenderingTestCase,
    WebRuleApplicabilityTestCase,
};

#[test]
fn given_every_core_rule_when_rendering_then_complete_authored_metadata_is_visible() {
    let test_cases = [CoreRuleRenderingTestCase {
        description: "every native core registration renders the complete stable metadata frame",
        expected_core_count: 112,
        expected_labels: &[
            "Authored metadata:",
            "Family:",
            "Severity:",
            "Kind: core",
            "Pack: None",
            "Alias: None",
            "Analyzers:",
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
            assert!(
                metadata.analyzers == [AnalyzerId::Python]
                    || metadata.analyzers == [AnalyzerId::Svelte]
                    || metadata.analyzers == [AnalyzerId::TypeScript, AnalyzerId::Svelte]
            );
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
        expected_codes: &[
            "FPTSA001", "FPTSA002", "FPTSA003", "FPTSC101", "FPTSC102", "FPTSC103", "FPTSH009",
            "FPTSL101", "FPTSL102", "FPTSL103", "FPTSL105", "FPTSL108", "FPTSL109", "FPTSL201",
            "FPTSN001", "FPTSN002", "FPTSN003", "FPTSN004", "FPTSP001", "FPTSR001", "FPTSR002",
            "FPTSR003", "FPTSR201", "FPTSR204", "FPTSR301", "FPTSR304", "FPTSR306", "FPTSR309",
            "FPTSR310", "FPTSR311", "FPTSR401", "FPTSR403", "FPTSR501", "FPTSS001", "FPTSS002",
            "FPTSS003", "FPTSS010", "FPTSS011", "FPTSS105", "FPTSS106", "FPTSS110", "FPTSS111",
            "FPTSS201", "FPTSS601", "FPTST001", "FPTST002", "FPTST003", "FPTST004", "FPTST201",
            "FPTST202", "FPTST302", "FPTST401", "FPTST402", "FPTST403", "FPTST404", "FPTST405",
            "FPTST406", "FPTST410", "FPTST411", "FPTST412",
        ],
        expected_error: None,
    }];
    let root = tempfile::tempdir().expect("catalogue selection root");
    for test_case in &test_cases {
        let config = Config {
            analyzer: test_case.analyzer,
            rule_packs: vec!["typescript".to_owned()],
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
        let mut actual_codes = selected
            .catalogue
            .iter()
            .map(|rule| rule.code.as_str())
            .collect::<Vec<_>>();
        actual_codes.sort_unstable();
        assert_eq!(
            actual_codes, test_case.expected_codes,
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
fn given_web_rule_applicability_when_selecting_then_analyzer_and_pack_activation_fail_closed() {
    let test_cases = [WebRuleApplicabilityTestCase {
        description: "Svelte-only and SvelteKit rules reject incompatible targets while generic remains shared",
        expected_analyzer_error: "not applicable to analyzer typescript",
        expected_missing_pack_error: "matches no rules in the configured catalogue",
        expected_generic_code: "FPTSS010",
    }];
    let root = tempfile::tempdir().expect("catalogue selection root");
    for test_case in &test_cases {
        let typescript = Config {
            analyzer: AnalyzerId::TypeScript,
            rule_packs: vec!["sveltekit".to_owned()],
            select: vec!["FPSKV101".to_owned()],
            ..Config::default()
        };
        let svelte_without_kit = Config {
            analyzer: AnalyzerId::Svelte,
            select: vec!["FPSKL106".to_owned()],
            ..Config::default()
        };
        let generic_svelte = Config {
            analyzer: AnalyzerId::Svelte,
            rule_packs: vec!["typescript".to_owned()],
            select: vec!["FPTSS010".to_owned()],
            ..Config::default()
        };

        let analyzer_error = selection::selection(&typescript, root.path())
            .expect_err("Svelte rule is incompatible with TypeScript");
        let missing_pack_error = selection::selection(&svelte_without_kit, root.path())
            .expect_err("SvelteKit rule requires its activated pack");
        let generic = selection::selection(&generic_svelte, root.path())
            .expect("generic web rule remains available to Svelte");

        assert!(
            analyzer_error.contains(test_case.expected_analyzer_error),
            "{}",
            test_case.description
        );
        assert!(
            missing_pack_error.contains(test_case.expected_missing_pack_error),
            "{}",
            test_case.description
        );
        assert_eq!(
            generic.blocking[0].code, test_case.expected_generic_code,
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
