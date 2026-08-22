//! Invalidate one reusable cache namespace.

use std::fs;
use std::path::Path;

use crate::lifecycle::_helpers::cache::{cache_error, cache_path};
use crate::lifecycle::errors::LifecycleError;

/// Remove one cache namespace and report whether it existed.
pub fn invalidate_cache(root: &Path, namespace: &str) -> Result<bool, LifecycleError> {
    let path = cache_path(root, namespace);
    match fs::remove_file(&path) {
        Ok(()) => Ok(true),
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(false),
        Err(error) => Err(cache_error(&path, error)),
    }
}
