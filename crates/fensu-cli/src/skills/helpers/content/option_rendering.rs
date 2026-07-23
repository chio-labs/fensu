use serde_json::json;

use crate::models::{RuleMetadata, RuleOptionMetadata, RuleOptionValue};
use crate::skills::helpers::content::sections::py_json;

pub(crate) fn rule_option_lines(rule: &RuleMetadata) -> Vec<String> {
    if rule.options.is_empty() {
        return Vec::new();
    }
    let mut options = rule.options.iter().collect::<Vec<_>>();
    options.sort_by(|left, right| left.name.cmp(&right.name));
    let mut lines = vec!["Options:".to_owned(), String::new()];
    for option in options {
        lines.push(format!("#### `{}`", option.name));
        lines.push(String::new());
        lines.extend(skill_option_fields(option));
        lines.push(String::new());
    }
    lines
}

fn skill_option_fields(option: &RuleOptionMetadata) -> Vec<String> {
    vec![
        format!("- Type: `{}`", skill_option_type(&option.kind)),
        format!("- Required: `{}`", option.required),
        format!(
            "- Default: {}",
            if option.required {
                "required".to_owned()
            } else {
                skill_option_value(option.default.as_ref())
            }
        ),
        format!(
            "- Current value: {}",
            skill_option_value(Some(&option.current_value))
        ),
        format!(
            "- Description: {}",
            option.description.as_deref().unwrap_or("None")
        ),
        format!(
            "- Choices: {}",
            option.choices.as_ref().map_or_else(
                || "None".to_owned(),
                |value| py_json(&json!(value)).unwrap_or_else(|_| "None".to_owned())
            )
        ),
        format!(
            "- Minimum: {}",
            option
                .minimum
                .map_or_else(|| "None".to_owned(), |value| value.to_string())
        ),
        format!(
            "- Maximum: {}",
            option
                .maximum
                .map_or_else(|| "None".to_owned(), |value| value.to_string())
        ),
        format!(
            "- Minimum items: {}",
            option
                .minimum_items
                .map_or_else(|| "None".to_owned(), |value| value.to_string())
        ),
    ]
}

fn skill_option_type(kind: &str) -> &str {
    match kind {
        "string_list" => "list[string]",
        "integer_list" => "list[integer]",
        other => other,
    }
}

fn skill_option_value(value: Option<&RuleOptionValue>) -> String {
    value.map_or_else(
        || "None".to_owned(),
        |value| py_json(&json!(value)).unwrap_or_else(|_| "None".to_owned()),
    )
}
