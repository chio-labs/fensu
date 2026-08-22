//! Repository-relative path validation and matching.

use globset::GlobBuilder;

use crate::lifecycle::constants::{
    CURRENT_PATH_SEGMENT, MATCH_ALL_PATH_PATTERN, PARENT_PATH_SEGMENT,
};
use crate::lifecycle::errors::LifecycleError;

pub(crate) fn validate_repository_path(path: &str) -> Result<(), LifecycleError> {
    if !canonical_posix_parts(path) {
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
    if !canonical_posix_parts(pattern) {
        return Err(LifecycleError::InvalidPathPattern {
            pattern: pattern.to_owned(),
        });
    }
    compiled_pattern(pattern)
        .map(|_| ())
        .map_err(|_| LifecycleError::InvalidPathPattern {
            pattern: pattern.to_owned(),
        })
}

fn canonical_posix_parts(value: &str) -> bool {
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
    if drive_prefix || !valid_part(first) {
        return false;
    }
    parts.all(valid_part)
}

fn valid_part(part: &str) -> bool {
    !part.is_empty() && part != CURRENT_PATH_SEGMENT && part != PARENT_PATH_SEGMENT
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
