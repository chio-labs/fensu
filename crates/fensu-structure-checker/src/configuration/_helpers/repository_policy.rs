//! Validate repository policy collections and paths.

use std::collections::HashSet;
use std::path::{Component, Path};

pub(crate) fn validate_non_empty_unique(values: &[String], name: &str) -> Result<(), String> {
    let mut unique: HashSet<&String> = HashSet::new();
    for value in values {
        if value.trim().is_empty() {
            return Err(format!("structure-checker {name} must not be empty"));
        }
        if !unique.insert(value) {
            return Err(format!(
                "structure-checker {name} contain duplicate {value}"
            ));
        }
    }
    Ok(())
}

pub(crate) fn valid_repository_path(value: &str) -> bool {
    let path = Path::new(value);
    !value.contains('\\')
        && !path.is_absolute()
        && path
            .components()
            .all(|part| matches!(part, Component::Normal(_)))
}
