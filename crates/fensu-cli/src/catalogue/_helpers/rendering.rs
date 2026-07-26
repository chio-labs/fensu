//! Render a rule's metadata, options, exceptions, and ignores.

use crate::catalogue::_helpers::options::option_lines;
use crate::models::{Config, RuleIgnore, RuleMetadata};
use crate::reporting::constants::{ORANGE, RESET};

pub(crate) fn render(metadata: &RuleMetadata, config: &Config, color: bool) -> String {
    let header = if color {
        format!("{ORANGE}{}{RESET} {}", metadata.code, metadata.slug)
    } else {
        format!("{} {}", metadata.code, metadata.slug)
    };
    let mut output = format!("{header}\n");
    output = render_metadata(output, metadata, color);
    output = render_constraints(output, metadata);
    output = render_thresholds(output, metadata, config);
    output = render_contracts(output, metadata, config);
    output = render_configuration_inputs(output, metadata, config);
    output = render_limits(output, metadata);
    output = render_options(output, metadata);
    output = render_exceptions(output, metadata, config);
    output = render_rule_ignores(output, metadata, config);
    output
}

pub(crate) fn render_limits(mut output: String, metadata: &RuleMetadata) -> String {
    if metadata.limits.is_empty() {
        return output;
    }
    let mut limits = metadata.limits.iter().collect::<Vec<_>>();
    limits.sort_by(|left, right| left.name.cmp(&right.name));
    output.push_str("\nFixed limits:\n");
    for limit in limits {
        output.push_str(&format!("  {}: {}\n", limit.description, limit.value));
    }
    output
}

pub(crate) fn render_configuration_inputs(
    mut output: String,
    metadata: &RuleMetadata,
    config: &Config,
) -> String {
    if metadata.configuration_inputs.is_empty() {
        return output;
    }
    let mut names = metadata.configuration_inputs.iter().collect::<Vec<_>>();
    names.sort();
    output.push_str("\nEffective configuration:\n");
    for name in names {
        let values = configuration_values(name, config);
        output.push_str(&format!("  {name}: {}\n", values.join(", ")));
    }
    output
}

fn configuration_values<'a>(name: &str, config: &'a Config) -> &'a [String] {
    match name {
        "roots" => &config.roots,
        "tests" => &config.tests,
        "tooling" => &config.tooling,
        "test_scopes" => &config.test_scopes,
        _ => &[],
    }
}

pub(crate) fn render_contracts(
    mut output: String,
    metadata: &RuleMetadata,
    config: &Config,
) -> String {
    let mut contracts = config
        .contracts
        .iter()
        .filter(|(_, behavior)| metadata.contract_behaviors.contains(behavior))
        .collect::<Vec<_>>();
    if contracts.is_empty() {
        return output;
    }
    contracts.sort();
    output.push_str("\nNaming contracts:\n");
    for (pattern, behavior) in contracts {
        output.push_str(&format!("  {pattern}: {behavior}\n"));
    }
    output
}

pub(crate) fn render_thresholds(
    mut output: String,
    metadata: &RuleMetadata,
    config: &Config,
) -> String {
    if metadata.thresholds.is_empty() {
        return output;
    }
    let mut thresholds = metadata.thresholds.iter().collect::<Vec<_>>();
    thresholds.sort();
    output.push_str("\nThresholds:\n");
    for name in thresholds {
        let value = config
            .thresholds
            .get(name)
            .map_or_else(|| "not configured".to_owned(), u32::to_string);
        output.push_str(&format!(
            "  {name}: {value} (base value; role or path overrides may apply)\n"
        ));
    }
    output
}

pub(crate) fn render_constraints(mut output: String, metadata: &RuleMetadata) -> String {
    if metadata.constraints.is_empty() {
        return output;
    }
    let mut constraints = metadata.constraints.iter().collect::<Vec<_>>();
    constraints.sort_by(|left, right| left.name.cmp(&right.name));
    output.push_str("\nConstraints:\n");
    for constraint in constraints {
        output.push_str(&format!(
            "  {}: {}\n",
            constraint.description,
            constraint.values.join(", ")
        ));
    }
    output
}

pub(crate) fn render_options(mut output: String, metadata: &RuleMetadata) -> String {
    if metadata.options.is_empty() {
        return output;
    }
    let mut options = metadata.options.iter().collect::<Vec<_>>();
    options.sort_by(|left, right| left.name.cmp(&right.name));
    output.push_str("\nOptions:\n");
    for option in options {
        output.push_str(&format!("  {}\n", option.name));
        for (label, value) in option_lines(option) {
            output.push_str(&format!("    {label}: {value}\n"));
        }
    }
    output
}

pub(crate) fn render_metadata(mut output: String, metadata: &RuleMetadata, color: bool) -> String {
    let enabled = if metadata.enabled_by_default {
        "yes"
    } else {
        "no"
    };
    for (label, value) in [
        ("Family", metadata.family.as_str()),
        ("Severity", metadata.severity.as_str()),
        ("Kind", metadata.kind.as_str()),
        ("Enabled by default", enabled),
        ("Source", metadata.source.as_deref().unwrap_or("core")),
        ("Message", metadata.message.as_str()),
        (
            "Remediation",
            metadata.remediation.as_deref().unwrap_or("None provided."),
        ),
    ] {
        if color {
            output.push_str(&format!("\x1b[2m{label}:\x1b[0m {value}\n"));
        } else {
            output.push_str(&format!("{label}: {value}\n"));
        }
    }
    output
}

pub(crate) fn render_exceptions(
    mut output: String,
    metadata: &RuleMetadata,
    config: &Config,
) -> String {
    let exceptions = config
        .exceptions
        .iter()
        .filter(|entry| entry.rule == metadata.code)
        .collect::<Vec<_>>();
    if exceptions.is_empty() {
        return output;
    }
    output.push_str("\nActive exceptions:\n");
    for exception in exceptions {
        let scope = if exception.symbols.is_empty() {
            "file-level".to_owned()
        } else {
            exception.symbols.join(", ")
        };
        output.push_str(&format!("  {}: {scope}\n", exception.path));
        output.push_str(&format!("    Reason: {}\n", exception.reason));
    }
    output
}

pub(crate) fn render_rule_ignores(
    mut output: String,
    metadata: &RuleMetadata,
    config: &Config,
) -> String {
    let mut ignores: Vec<&RuleIgnore> = Vec::new();
    for entry in &config.rule_ignores {
        if entry
            .rules
            .iter()
            .any(|selector| metadata.code.starts_with(selector))
        {
            ignores.push(entry);
        }
    }
    if ignores.is_empty() {
        return output;
    }
    output.push_str("\nActive path-scoped rule ignores:\n");
    for entry in ignores {
        output.push_str(&format!("  {}\n", entry.paths.join(", ")));
        output.push_str(&format!("    Reason: {}\n", entry.reason));
    }
    output
}
