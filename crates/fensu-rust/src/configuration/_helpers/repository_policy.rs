//! Validate repository policy collections and paths.

use std::collections::HashSet;

use crate::constants::{CURRENT_PATH_SEGMENT, PARENT_PATH_SEGMENT};

pub(crate) fn default_raw_parser_restricted_paths() -> Vec<String> {
    crate::constants::DEFAULT_RAW_PARSER_RESTRICTED_PATHS
        .iter()
        .map(|value| (*value).to_owned())
        .collect()
}

pub(crate) fn validate_non_empty_unique(values: &[String], name: &str) -> Result<(), String> {
    let mut unique: HashSet<&String> = HashSet::new();
    for value in values {
        if value.trim().is_empty() {
            return Err(format!("Rust rule policy {name} must not be empty"));
        }
        if !unique.insert(value) {
            return Err(format!("Rust rule policy {name} contain duplicate {value}"));
        }
    }
    Ok(())
}

pub(crate) fn valid_repository_path(value: &str) -> bool {
    if value.is_empty() || value.starts_with('/') || value.contains('\\') || value.contains('\0') {
        return false;
    }
    let mut parts = value.split('/');
    let Some(first) = parts.next() else {
        return false;
    };
    let bytes = first.as_bytes();
    let drive_prefix =
        bytes.first().is_some_and(u8::is_ascii_alphabetic) && bytes.get(1) == Some(&b':');
    !drive_prefix && valid_part(first) && parts.all(valid_part)
}

fn valid_part(value: &str) -> bool {
    !value.is_empty() && value != CURRENT_PATH_SEGMENT && value != PARENT_PATH_SEGMENT
}
