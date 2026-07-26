//! Render one rule's documentation for the rule command.

use std::path::Path;

use crate::catalogue::_helpers::arguments::{parse_arguments, use_color};
use crate::catalogue::_helpers::loading::rule_catalogue;
use crate::catalogue::_helpers::rendering::render;
use crate::configuration::main::load;
use crate::skills::main::catalogue::load_rule_catalogue;

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
        rule_catalogue().to_vec()
    } else {
        load_rule_catalogue(&loaded, project_root)?
    };
    let metadata = catalogue
        .iter()
        .find(|metadata| metadata.code == code)
        .ok_or_else(|| format!("Unknown rule code: {code}"))?;
    Ok(render(metadata, &loaded, use_color(&color)))
}
