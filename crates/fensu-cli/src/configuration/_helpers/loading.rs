use std::fs;
use std::path::{Path, PathBuf};

use crate::configuration::_helpers::roots::resolve_target_root;
use crate::configuration::_helpers::{discovery, parsing, validation};
use crate::models::Config;

pub(crate) fn load(start: &Path) -> Result<(PathBuf, Config), String> {
    load_target(start, None)
}

pub(crate) fn load_target(start: &Path, target: Option<&str>) -> Result<(PathBuf, Config), String> {
    let (path, pyproject) = discovery::find(start)?;
    let raw =
        fs::read(&path).map_err(|error| format!("Could not read {}: {error}", path.display()))?;
    let document = toml::from_slice::<toml::Value>(&raw)
        .map_err(|error| format!("Could not parse {}: {error}", path.display()))?;
    let value = if pyproject {
        document
            .get("tool")
            .and_then(|value| value.get("fensu"))
            .ok_or_else(|| format!("{} does not contain [tool.fensu].", path.display()))?
    } else {
        &document
    };
    let table = value.as_table().ok_or_else(|| {
        format!(
            "Config source {} did not contain a TOML table.",
            path.display()
        )
    })?;
    let selection = validation::select_target(table, target)?;
    validation::validate_for_analyzer(&selection.table, selection.analyzer)?;
    let config = parsing::build(selection, raw, pyproject)?;
    let repository_root = path
        .parent()
        .ok_or_else(|| "Configuration has no parent directory.".to_owned())?;
    let _ = resolve_target_root(repository_root, &config.target_root)?;
    Ok((path, config))
}

pub(crate) fn load_targets(
    start: &Path,
    target: Option<&str>,
) -> Result<Vec<(PathBuf, Config)>, String> {
    let (path, pyproject) = discovery::find(start)?;
    let raw =
        fs::read(&path).map_err(|error| format!("Could not read {}: {error}", path.display()))?;
    let document = toml::from_slice::<toml::Value>(&raw)
        .map_err(|error| format!("Could not parse {}: {error}", path.display()))?;
    let value = if pyproject {
        document
            .get("tool")
            .and_then(|value| value.get("fensu"))
            .ok_or_else(|| format!("{} does not contain [tool.fensu].", path.display()))?
    } else {
        &document
    };
    let table = value.as_table().ok_or_else(|| {
        format!(
            "Config source {} did not contain a TOML table.",
            path.display()
        )
    })?;
    let names = validation::selected_target_names(table, target)?;
    names
        .into_iter()
        .map(|name| load_target(start, name.as_deref()))
        .collect()
}

pub(crate) fn load_optional(
    start: &Path,
    target: Option<&str>,
) -> Result<Option<(PathBuf, Config)>, String> {
    match discovery::find(start) {
        Ok(_) => match target {
            Some(target) => load_target(start, Some(target)).map(Some),
            None => load(start).map(Some),
        },
        Err(error) if error.starts_with("Could not find fensu.toml") => Ok(None),
        Err(error) => Err(error),
    }
}

pub(crate) fn custom_rules_are_configured(
    start: &Path,
    target: Option<&str>,
) -> Result<bool, String> {
    Ok(load_targets(start, target)?
        .into_iter()
        .any(config_has_custom_rules))
}

fn config_has_custom_rules((_, config): (PathBuf, Config)) -> bool {
    !config.rule_paths.is_empty()
        || !config.rule_modules.is_empty()
        || config.rule_options.keys().any(|code| code.starts_with('X'))
}
