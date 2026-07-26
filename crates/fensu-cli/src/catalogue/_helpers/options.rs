//! Render one rule option's metadata lines.

use crate::models::{RuleOptionMetadata, RuleOptionValue};

pub(crate) fn option_lines(option: &RuleOptionMetadata) -> [(&'static str, String); 9] {
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

pub(crate) fn option_type(kind: &str) -> &str {
    match kind {
        "string_list" => "list[string]",
        "integer_list" => "list[integer]",
        other => other,
    }
}

pub(crate) fn option_value(value: Option<&RuleOptionValue>) -> String {
    value.map_or_else(
        || "None".to_owned(),
        |value| serde_json::to_string(value).unwrap_or_else(|_| "null".to_owned()),
    )
}

pub(crate) fn optional_number(value: Option<i64>) -> String {
    value.map_or_else(|| "None".to_owned(), |value| value.to_string())
}
