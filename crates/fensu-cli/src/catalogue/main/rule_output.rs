//! Render one rule's documentation for the rule command.

use std::path::Path;

use crate::catalogue::_helpers::arguments::{parse_arguments, use_color};
use crate::catalogue::_helpers::rendering::render;
use crate::catalogue::main::rule_catalogue::configured_rule_catalogue;
use crate::configuration::main::load;
use crate::models::{RuleOptionListValue, RuleOptionValue};
use crate::skills::main::catalogue::load_rule_catalogue;

pub(crate) fn rule_output(arguments: &[String]) -> Result<String, String> {
    let (color, code) = parse_arguments(arguments)?;
    let (config_path, loaded) = load::load(Path::new("."))?;
    let project_root = config_path
        .parent()
        .ok_or_else(|| "Configuration has no parent directory.".to_owned())?;
    let mut catalogue = if loaded.rule_paths.is_empty()
        && loaded.rule_modules.is_empty()
        && !loaded.rule_options.keys().any(|code| code.starts_with('X'))
    {
        configured_rule_catalogue(&loaded.rule_packs)
            .into_iter()
            .cloned()
            .collect()
    } else {
        load_rule_catalogue(&loaded, project_root)?
    };
    apply_native_option_values(&mut catalogue, &loaded)?;
    let metadata = catalogue
        .iter()
        .find(|metadata| metadata.code == code)
        .ok_or_else(|| format!("Unknown rule code: {code}"))?;
    Ok(render(metadata, &loaded, use_color(&color)))
}

fn apply_native_option_values(
    catalogue: &mut [crate::models::RuleMetadata],
    config: &crate::models::Config,
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
