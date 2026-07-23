use std::env;
use std::io::{self, IsTerminal};
use std::path::Path;
use std::sync::OnceLock;

use crate::configuration::main::load;
use crate::constants::{COLOR_ALWAYS, COLOR_AUTO, COLOR_NEVER, OPTION_COLOR};
use crate::models::{Config, RuleMetadata, RuleOptionMetadata, RuleOptionValue};
use crate::skills::main::catalogue::load_rule_catalogue;

static CATALOGUE: OnceLock<Vec<RuleMetadata>> = OnceLock::new();

pub(crate) fn core_kind() -> String {
    "core".to_owned()
}

pub(crate) fn cacheable_default() -> bool {
    false
}

pub(crate) fn rule_output(arguments: &[String]) -> Result<String, String> {
    let (color, code) = parse_arguments(arguments)?;
    let (config_path, loaded) = load::load(Path::new("."))?;
    let project_root = config_path
        .parent()
        .ok_or_else(|| "Configuration has no parent directory.".to_owned())?;
    let catalogue = if loaded.rule_paths.is_empty()
        && loaded.rule_modules.is_empty()
        && loaded.rule_options.is_empty()
    {
        catalogue().to_vec()
    } else {
        load_rule_catalogue(&loaded, project_root)?
    };
    let metadata = catalogue
        .iter()
        .find(|metadata| metadata.code == code)
        .ok_or_else(|| format!("Unknown rule code: {code}"))?;
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
    render_options(&mut output, metadata);
    render_exceptions(&mut output, metadata, config);
    render_rule_ignores(&mut output, metadata, config);
    output
}

fn render_options(output: &mut String, metadata: &RuleMetadata) {
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

fn option_lines(option: &RuleOptionMetadata) -> [(&'static str, String); 9] {
    [
        ("Type", option_type(&option.kind).to_owned()),
        ("Required", option.required.to_string()),
        (
            "Default",
            if option.required {
                "required".to_owned()
            } else {
                option_value(option.default.as_ref())
            },
        ),
        ("Current value", option_value(Some(&option.current_value))),
        (
            "Description",
            option
                .description
                .clone()
                .unwrap_or_else(|| "None".to_owned()),
        ),
        (
            "Choices",
            serde_json::to_string(&option.choices).unwrap_or_else(|_| "null".to_owned()),
        ),
        ("Minimum", optional_number(option.minimum)),
        ("Maximum", optional_number(option.maximum)),
        (
            "Minimum items",
            option
                .minimum_items
                .map_or_else(|| "None".to_owned(), |value| value.to_string()),
        ),
    ]
}

fn option_type(kind: &str) -> &str {
    match kind {
        "string_list" => "list[string]",
        "integer_list" => "list[integer]",
        other => other,
    }
}

fn option_value(value: Option<&RuleOptionValue>) -> String {
    value.map_or_else(
        || "None".to_owned(),
        |value| serde_json::to_string(value).unwrap_or_else(|_| "null".to_owned()),
    )
}

fn optional_number(value: Option<i64>) -> String {
    value.map_or_else(|| "None".to_owned(), |value| value.to_string())
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

fn render_rule_ignores(output: &mut String, metadata: &RuleMetadata, config: &Config) {
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
