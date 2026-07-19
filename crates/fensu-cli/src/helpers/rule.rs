use std::env;
use std::io::{self, IsTerminal};
use std::path::Path;
use std::sync::OnceLock;

use crate::constants::{COLOR_ALWAYS, COLOR_AUTO, COLOR_NEVER, OPTION_COLOR};
use crate::helpers::config;
use crate::models::{Config, RuleMetadata};

static CATALOGUE: OnceLock<Vec<RuleMetadata>> = OnceLock::new();

pub(crate) fn rule_output(arguments: &[String]) -> Result<String, String> {
    let (color, code) = parse_arguments(arguments)?;
    let metadata = rule(&code).ok_or_else(|| format!("Unknown rule code: {code}"))?;
    let (_, loaded) = config::load(Path::new("."))?;
    Ok(render(metadata, &loaded, use_color(&color)))
}

pub(crate) fn catalogue() -> &'static [RuleMetadata] {
    CATALOGUE
        .get_or_init(|| {
            serde_json::from_slice(include_bytes!(concat!(env!("OUT_DIR"), "/catalogue.json")))
                .unwrap_or_default()
        })
        .as_slice()
}

pub(crate) fn rule(code: &str) -> Option<&'static RuleMetadata> {
    catalogue().iter().find(|rule| rule.code == code)
}

fn parse_arguments(arguments: &[String]) -> Result<(String, String), String> {
    let mut color = COLOR_AUTO.to_owned();
    let mut code = None;
    let mut index = 0;
    while index < arguments.len() {
        if arguments[index] == OPTION_COLOR {
            index += 1;
            color = arguments.get(index).cloned().ok_or_else(|| {
                "fensu rule: error: argument --color: expected one argument".to_owned()
            })?;
            if !matches!(color.as_str(), COLOR_AUTO | COLOR_ALWAYS | COLOR_NEVER) {
                return Err(format!("fensu rule: error: invalid choice: '{color}'"));
            }
        } else if arguments[index].starts_with('-') {
            return Err(format!(
                "fensu rule: error: unrecognized arguments: {}",
                arguments[index]
            ));
        } else {
            code = Some(arguments[index].clone());
        }
        index += 1;
    }
    let code = code.ok_or_else(|| {
        "fensu rule: error: the following arguments are required: code".to_owned()
    })?;
    Ok((color, code))
}

fn use_color(color: &str) -> bool {
    env::var_os("NO_COLOR").is_none()
        && (color == COLOR_ALWAYS || color == COLOR_AUTO && io::stdout().is_terminal())
}

fn render(metadata: &RuleMetadata, config: &Config, color: bool) -> String {
    let header = if color {
        format!("\x1b[1;36m{}\x1b[0m {}", metadata.code, metadata.slug)
    } else {
        format!("{} {}", metadata.code, metadata.slug)
    };
    let mut output = format!("{header}\n");
    render_metadata(&mut output, metadata, color);
    render_exceptions(&mut output, metadata, config);
    output
}

fn render_metadata(output: &mut String, metadata: &RuleMetadata, color: bool) {
    let enabled = if metadata.enabled_by_default {
        "yes"
    } else {
        "no"
    };
    for (label, value) in [
        ("Family", metadata.family.as_str()),
        ("Severity", metadata.severity.as_str()),
        ("Kind", "core"),
        ("Enabled by default", enabled),
        ("Source", "core"),
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

fn render_exceptions(output: &mut String, metadata: &RuleMetadata, config: &Config) {
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
