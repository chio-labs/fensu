//! Exhaustive authored metadata rendering contracts for core rules.

use crate::catalogue::_helpers::loading::rule_catalogue;
use crate::catalogue::_helpers::policy::RulePolicy;
use crate::catalogue::_helpers::rendering::render;
use crate::models::Config;
use crate::tests::test_types::CoreRuleRenderingTestCase;

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
        }
    }
}
