//! Resolve loaded policy and native option values for rule inspection.

use crate::catalogue::models::{RuleMetadata, RuleOptionListValue, RuleOptionValue};
use crate::models::Config;
use crate::skills::models::RuleSelection;

pub(crate) struct RulePolicy {
    pub(crate) selected: bool,
    pub(crate) blocking: bool,
    pub(crate) warning: bool,
    pub(crate) ignored: bool,
}

pub(crate) fn effective_policy(
    metadata: &RuleMetadata,
    config: &Config,
    selection: &RuleSelection,
) -> RulePolicy {
    RulePolicy {
        selected: requested(metadata, &config.select) || requested(metadata, &config.warn),
        blocking: contains_code(&selection.blocking, &metadata.code),
        warning: contains_code(&selection.warnings, &metadata.code),
        ignored: contains_code(&selection.ignored, &metadata.code),
    }
}

pub(crate) fn apply_native_option_values(
    catalogue: &mut [RuleMetadata],
    config: &Config,
) -> Result<(), String> {
    for metadata in catalogue {
        if metadata.pack.is_none() {
            continue;
        }
        let Some(values) = config
            .rule_options
            .get(&metadata.code)
            .and_then(toml::Value::as_table)
        else {
            continue;
        };
        for option in &mut metadata.options {
            let Some(value) = values.get(&option.name) else {
                continue;
            };
            let list = value.as_array().ok_or_else(|| {
                format!(
                    "Rule {} option {} must be a list.",
                    metadata.code, option.name
                )
            })?;
            option.current_value = RuleOptionValue::List(
                list.iter()
                    .filter_map(toml::Value::as_str)
                    .map(|item| RuleOptionListValue::String(item.to_owned()))
                    .collect(),
            );
        }
    }
    Ok(())
}

fn contains_code(rules: &[RuleMetadata], code: &str) -> bool {
    rules.iter().any(|metadata| metadata.code == code)
}

fn requested(metadata: &RuleMetadata, selectors: &[String]) -> bool {
    let matched = selectors
        .iter()
        .any(|selector| metadata.code.starts_with(selector));
    let explicit = selectors.iter().any(|selector| selector == &metadata.code);
    metadata.enabled_by_default && matched || explicit
}
