//! Render canonical rule contracts into generated skill sections.

use crate::catalogue::models::RuleMetadata;
use crate::models::Config;
use crate::skills::_helpers::content::option_rendering::rule_option_lines;

const CONTRACTS_CONFIGURATION_INPUT: &str = "contracts";
const TEST_LAYOUT_CONFIGURATION_INPUT: &str = "test_layout";
const UI_KIT_CONFIGURATION_INPUT: &str = "ui_kit";

pub(crate) fn tier_lines(heading: &str, rules: &[RuleMetadata], config: &Config) -> Vec<String> {
    let mut lines = vec![format!("## {heading}"), String::new()];
    if rules.is_empty() {
        lines.extend(["None.".to_owned(), String::new()]);
        return lines;
    }
    let mut rules = rules.iter().collect::<Vec<_>>();
    rules.sort_by(|left, right| left.code.cmp(&right.code));
    for rule in rules {
        lines.extend([
            format!("### {}: {}", rule.code, rule.slug),
            String::new(),
            format!("Family: `{}`", rule.family),
            format!(
                "Analyzers: {}",
                rule.analyzers
                    .iter()
                    .map(|analyzer| format!("`{analyzer}`"))
                    .collect::<Vec<_>>()
                    .join(", ")
            ),
            String::new(),
            rule.message.clone(),
            String::new(),
            format!(
                "Remediation: {}",
                rule.remediation
                    .as_deref()
                    .unwrap_or("No remediation provided.")
            ),
            String::new(),
        ]);
        lines.extend(rule_constraint_lines(rule));
        lines.extend(rule_threshold_lines(rule, config));
        lines.extend(rule_contract_lines(rule, config));
        lines.extend(rule_configuration_lines(rule, config));
        lines.extend(rule_limit_lines(rule));
        lines.extend(rule_option_lines(rule));
    }
    lines
}

fn rule_limit_lines(rule: &RuleMetadata) -> Vec<String> {
    if rule.limits.is_empty() {
        return Vec::new();
    }
    let mut lines = vec!["Fixed limits:".to_owned(), String::new()];
    let mut limits = rule.limits.iter().collect::<Vec<_>>();
    limits.sort_by(|left, right| left.name.cmp(&right.name));
    for limit in limits {
        lines.push(format!("- {}: `{}`", limit.description, limit.value));
    }
    lines.push(String::new());
    lines
}

fn rule_configuration_lines(rule: &RuleMetadata, config: &Config) -> Vec<String> {
    if rule.configuration_inputs.is_empty() {
        return Vec::new();
    }
    let mut lines = vec!["Effective configuration:".to_owned(), String::new()];
    let mut names = rule.configuration_inputs.iter().collect::<Vec<_>>();
    names.sort();
    for name in names {
        if name == CONTRACTS_CONFIGURATION_INPUT {
            let mut contracts = config.contracts.iter().collect::<Vec<_>>();
            contracts.sort();
            lines.push(format!(
                "- `contracts`: {}",
                contracts
                    .iter()
                    .map(|(pattern, behavior)| format!("`{pattern}` = `{behavior}`"))
                    .collect::<Vec<_>>()
                    .join(", ")
            ));
            continue;
        }
        if name == UI_KIT_CONFIGURATION_INPUT {
            lines.push(format!(
                "- `ui_kit`: {}",
                config.ui_kit.as_deref().unwrap_or("not configured")
            ));
            continue;
        }
        if matches!(name.as_str(), "framework" | "shadcn" | "openapi") {
            let value = match name.as_str() {
                "framework" => config.framework.as_deref(),
                "shadcn" => config.shadcn.as_deref(),
                "openapi" => config.openapi.as_deref(),
                _ => None,
            };
            lines.push(format!("- `{name}`: {}", value.unwrap_or("not configured")));
            continue;
        }
        if name == TEST_LAYOUT_CONFIGURATION_INPUT {
            lines.push(format!("- `test_layout`: {}", config.test_layout));
            continue;
        }
        let values = match name.as_str() {
            "roots" => &config.roots,
            "tests" => &config.tests,
            "tooling" => &config.tooling,
            "generated" => &config.generated,
            "test_scopes" => &config.test_scopes,
            _ => continue,
        };
        lines.push(format!("- `{name}`: `{}`", values.join("`, `")));
    }
    lines.push(String::new());
    lines
}

fn rule_contract_lines(rule: &RuleMetadata, config: &Config) -> Vec<String> {
    let mut matching = config
        .contracts
        .iter()
        .filter(|(_, behavior)| rule.contract_behaviors.contains(behavior))
        .collect::<Vec<_>>();
    if matching.is_empty() {
        return Vec::new();
    }
    matching.sort();
    let mut lines = vec!["Naming contracts:".to_owned(), String::new()];
    for (pattern, behavior) in matching {
        lines.push(format!("- `{pattern}`: `{behavior}`"));
    }
    lines.push(String::new());
    lines
}

fn rule_constraint_lines(rule: &RuleMetadata) -> Vec<String> {
    if rule.constraints.is_empty() {
        return Vec::new();
    }
    let mut lines = vec!["Constraints:".to_owned(), String::new()];
    let mut constraints = rule.constraints.iter().collect::<Vec<_>>();
    constraints.sort_by(|left, right| left.name.cmp(&right.name));
    for constraint in constraints {
        lines.push(format!(
            "- {}: {}",
            constraint.description,
            constraint
                .values
                .iter()
                .map(|value| format!("`{value}`"))
                .collect::<Vec<_>>()
                .join(", ")
        ));
    }
    lines.push(String::new());
    lines
}

fn rule_threshold_lines(rule: &RuleMetadata, config: &Config) -> Vec<String> {
    if rule.thresholds.is_empty() {
        return Vec::new();
    }
    let mut lines = vec!["Thresholds:".to_owned(), String::new()];
    let mut names = rule.thresholds.iter().collect::<Vec<_>>();
    names.sort();
    for name in names {
        let value = config
            .thresholds
            .get(name)
            .map_or_else(|| "not configured".to_owned(), u32::to_string);
        lines.push(format!(
            "- `{name}`: `{value}` (base value; role or path overrides may apply)"
        ));
    }
    lines.push(String::new());
    lines
}
