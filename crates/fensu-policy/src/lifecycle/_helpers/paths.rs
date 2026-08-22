//! Repository-relative path validation and matching.

use std::path::{Component, Path};

use globset::GlobBuilder;

use crate::lifecycle::constants::MATCH_ALL_PATH_PATTERN;
use crate::lifecycle::errors::LifecycleError;

pub(crate) fn validate_repository_path(path: &str) -> Result<(), LifecycleError> {
    let candidate = Path::new(path);
    let invalid = path.is_empty()
        || path.contains('\\')
        || candidate.is_absolute()
        || candidate
            .components()
            .any(|part| !matches!(part, Component::Normal(_)));
    if invalid {
        return Err(LifecycleError::InvalidRepositoryPath {
            path: path.to_owned(),
        });
    }
    Ok(())
}

pub(crate) fn matches(path: &str, pattern: &str) -> bool {
    match compiled_pattern(pattern) {
        Ok(glob) => glob.compile_matcher().is_match(path),
        Err(_) => false,
    }
}

pub(crate) fn validate_pattern(pattern: &str) -> Result<(), LifecycleError> {
    compiled_pattern(pattern)
        .map(|_| ())
        .map_err(|_| LifecycleError::InvalidPathPattern {
            pattern: pattern.to_owned(),
        })
}

fn compiled_pattern(pattern: &str) -> Result<globset::Glob, globset::Error> {
    let pattern = if pattern.contains('/') || pattern == MATCH_ALL_PATH_PATTERN {
        pattern.to_owned()
    } else {
        format!("**/{pattern}")
    };
    GlobBuilder::new(&pattern)
        .literal_separator(true)
        .backslash_escape(false)
        .build()
}
