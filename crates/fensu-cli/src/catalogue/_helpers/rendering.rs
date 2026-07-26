//! Render a rule's metadata, options, exceptions, and ignores.

use crate::catalogue::_helpers::options::option_lines;
use crate::models::{Config, RuleMetadata};

pub(crate) fn render(metadata: &RuleMetadata, config: &Config, color: bool) -> String {
    let header = if color {
        format!("\x1b[1;36m{}\x1b[0m {}", metadata.code, metadata.slug)
    } else {
        format!("{} {}", metadata.code, metadata.slug)
    };
    let mut output = format!("{header}\n");
    render_metadata(&mut output, metadata, color);
    render_options(&mut output, metadata);
    render_exceptions(&mut output, metadata, config);
    render_rule_ignores(&mut output, metadata, config);
    output
}

pub(crate) fn render_options(output: &mut String, metadata: &RuleMetadata) {
    if metadata.options.is_empty() {
        return;
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
}

pub(crate) fn render_metadata(output: &mut String, metadata: &RuleMetadata, color: bool) {
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
}

pub(crate) fn render_exceptions(output: &mut String, metadata: &RuleMetadata, config: &Config) {
    let exceptions = config
        .exceptions
        .iter()
        .filter(|entry| entry.rule == metadata.code)
        .collect::<Vec<_>>();
    if exceptions.is_empty() {
        return;
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
}

pub(crate) fn render_rule_ignores(output: &mut String, metadata: &RuleMetadata, config: &Config) {
    let ignores = config
        .rule_ignores
        .iter()
        .filter(|entry| {
            entry
                .rules
                .iter()
                .any(|selector| metadata.code.starts_with(selector))
        })
        .collect::<Vec<_>>();
    if ignores.is_empty() {
        return;
    }
    output.push_str("\nActive path-scoped rule ignores:\n");
    for entry in ignores {
        output.push_str(&format!("  {}\n", entry.paths.join(", ")));
        output.push_str(&format!("    Reason: {}\n", entry.reason));
    }
}
