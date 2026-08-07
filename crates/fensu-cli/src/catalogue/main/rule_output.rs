//! Render one rule's documentation for the rule command.

use std::path::Path;

use crate::catalogue::_helpers::arguments::{parse_arguments, use_color};
use crate::catalogue::_helpers::policy::{apply_native_option_values, effective_policy};
use crate::catalogue::_helpers::rendering::render;
use crate::configuration::main::load;
use crate::skills::main::catalogue::load_rule_selection;

pub(crate) fn rule_output(arguments: &[String]) -> Result<String, String> {
    let (color, code) = parse_arguments(arguments)?;
    let (config_path, loaded) = load::load(Path::new("."))?;
    let project_root = config_path
        .parent()
        .ok_or_else(|| "Configuration has no parent directory.".to_owned())?;
    let mut selection = load_rule_selection(&loaded, project_root)?;
    apply_native_option_values(&mut selection.catalogue, &loaded)?;
    let metadata = selection
        .catalogue
        .iter()
        .find(|metadata| metadata.code == code)
        .ok_or_else(|| format!("Unknown rule code: {code}"))?;
    let policy = effective_policy(metadata, &loaded, &selection);
    Ok(render(metadata, &loaded, use_color(&color), &policy))
}
