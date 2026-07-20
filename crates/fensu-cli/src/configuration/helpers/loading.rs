use std::fs;
use std::path::{Path, PathBuf};

use crate::configuration::helpers::{discovery, parsing, validation};
use crate::models::Config;

pub(crate) fn load(start: &Path) -> Result<(PathBuf, Config), String> {
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
    validation::validate(table)?;
    Ok((path, parsing::build(table, raw, pyproject)?))
}

pub(crate) fn load_optional(start: &Path) -> Result<Option<(PathBuf, Config)>, String> {
    match discovery::find(start) {
        Ok(_) => load(start).map(Some),
        Err(error) if error.starts_with("Could not find fensu.toml") => Ok(None),
        Err(error) => Err(error),
    }
}

pub(crate) fn custom_rules_are_configured(start: &Path) -> Result<bool, String> {
    let (_, config) = load(start)?;
    Ok(!config.rule_paths.is_empty() || !config.rule_modules.is_empty())
}
