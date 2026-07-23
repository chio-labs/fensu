use std::collections::HashSet;

use crate::models::{RuleMetadata, RuleOptionListValue, RuleOptionMetadata, RuleOptionValue};

const INTEGER_KIND: &str = "integer";
const INTEGER_LIST_KIND: &str = "integer_list";
const STRING_KIND: &str = "string";
const STRING_LIST_KIND: &str = "string_list";

pub(crate) fn validate_rule_options(rule: &RuleMetadata) -> Result<(), String> {
    let mut names = HashSet::new();
    for option in &rule.options {
        if !valid_option_name(&option.name)
            || !names.insert(option.name.as_str())
            || option.required == option.default.is_some()
            || !option_value_matches_kind(&option.current_value, &option.kind)
            || option
                .default
                .as_ref()
                .is_some_and(|value| !option_value_matches_kind(value, &option.kind))
            || option
                .description
                .as_deref()
                .is_some_and(|description| description.trim().is_empty())
            || !valid_option_constraints(option)
        {
            return Err(format!(
                "Catalogue rule {} option {} contains incompatible metadata.",
                rule.code, option.name
            ));
        }
    }
    Ok(())
}

fn valid_option_name(name: &str) -> bool {
    !name.is_empty()
        && name.split('_').all(|part| {
            !part.is_empty()
                && part.as_bytes()[0].is_ascii_lowercase()
                && part
                    .as_bytes()
                    .iter()
                    .all(|byte| byte.is_ascii_lowercase() || byte.is_ascii_digit())
        })
}

fn option_value_matches_kind(value: &RuleOptionValue, kind: &str) -> bool {
    match (kind, value) {
        ("boolean", RuleOptionValue::Boolean(_))
        | (INTEGER_KIND, RuleOptionValue::Integer(_))
        | (STRING_KIND, RuleOptionValue::String(_)) => true,
        (STRING_LIST_KIND, RuleOptionValue::List(values)) => values
            .iter()
            .all(|value| matches!(value, RuleOptionListValue::String(_))),
        (INTEGER_LIST_KIND, RuleOptionValue::List(values)) => values
            .iter()
            .all(|value| matches!(value, RuleOptionListValue::Integer(_))),
        _ => false,
    }
}

fn valid_option_constraints(option: &RuleOptionMetadata) -> bool {
    let choices_valid = match (&option.kind[..], &option.choices) {
        (STRING_KIND, Some(choices)) => {
            !choices.is_empty()
                && choices.iter().collect::<HashSet<_>>().len() == choices.len()
                && option_values_in_choices(option, choices)
        }
        (STRING_KIND, None) => true,
        (_, None) => true,
        (_, Some(_)) => false,
    };
    let integer_bounds_valid = if option.kind == INTEGER_KIND {
        option
            .minimum
            .zip(option.maximum)
            .is_none_or(|(min, max)| min <= max)
            && option_values_in_bounds(option)
    } else {
        option.minimum.is_none() && option.maximum.is_none()
    };
    let minimum_items_valid =
        if matches!(option.kind.as_str(), STRING_LIST_KIND | INTEGER_LIST_KIND) {
            option
                .minimum_items
                .is_none_or(|minimum| option_values_have_minimum_items(option, minimum))
        } else {
            option.minimum_items.is_none()
        };
    choices_valid && integer_bounds_valid && minimum_items_valid
}

fn option_values_in_choices(option: &RuleOptionMetadata, choices: &[String]) -> bool {
    [
        &option.current_value,
        option.default.as_ref().unwrap_or(&option.current_value),
    ]
    .into_iter()
    .all(|value| matches!(value, RuleOptionValue::String(value) if choices.contains(value)))
}

fn option_values_in_bounds(option: &RuleOptionMetadata) -> bool {
    [
        &option.current_value,
        option.default.as_ref().unwrap_or(&option.current_value),
    ]
    .into_iter()
    .all(|value| {
        matches!(value, RuleOptionValue::Integer(value)
                if option.minimum.is_none_or(|minimum| *value >= minimum)
                    && option.maximum.is_none_or(|maximum| *value <= maximum))
    })
}

fn option_values_have_minimum_items(option: &RuleOptionMetadata, minimum: usize) -> bool {
    [
        &option.current_value,
        option.default.as_ref().unwrap_or(&option.current_value),
    ]
    .into_iter()
    .all(|value| matches!(value, RuleOptionValue::List(values) if values.len() >= minimum))
}
