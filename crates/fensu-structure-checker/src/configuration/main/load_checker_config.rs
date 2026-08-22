//! Load one explicit versioned checker configuration.

use std::fs;
use std::path;

use crate::models;

/// Read, parse, and validate one structure-checker TOML file.
pub fn load_checker_config(path: &path::Path) -> Result<models::CheckerConfig, String> {
    let source = fs::read_to_string(path).map_err(|error| {
        format!(
            "could not read structure-checker config {}: {error}",
            path.display()
        )
    })?;
    let config = toml::from_str::<models::CheckerConfig>(&source).map_err(|error| {
        format!(
            "could not parse structure-checker config {}: {error}",
            path.display()
        )
    })?;
    config.validate()?;
    Ok(config)
}
