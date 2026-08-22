//! Write one reusable cache namespace.

use std::fs;
use std::path::Path;

use serde::Serialize;

use crate::lifecycle::_helpers::cache::{
    cache_error, cache_path, temporary_cache_path, CacheEnvelope,
};
use crate::lifecycle::_helpers::canonical;
use crate::lifecycle::constants::CACHE_SCHEMA_VERSION;
use crate::lifecycle::errors::LifecycleError;

/// Replace one namespace with a value for the supplied identity.
pub fn write_cache<T: Serialize>(
    root: &Path,
    namespace: &str,
    identity: &str,
    value: &T,
) -> Result<(), LifecycleError> {
    let path = cache_path(root, namespace);
    let parent = path.parent().ok_or_else(|| LifecycleError::CacheIo {
        message: format!("cache path has no parent: {}", path.display()),
    })?;
    fs::create_dir_all(parent).map_err(|error| cache_error(parent, error))?;
    let envelope = CacheEnvelope {
        schema: CACHE_SCHEMA_VERSION,
        identity: identity.to_owned(),
        value,
    };
    let data = canonical::canonical_json(&envelope)?;
    let temporary = temporary_cache_path(&path);
    fs::write(&temporary, data).map_err(|error| cache_error(&temporary, error))?;
    if let Err(first_error) = fs::rename(&temporary, &path) {
        if !path.exists()
            || fs::remove_file(&path).is_err()
            || fs::rename(&temporary, &path).is_err()
        {
            let _ = fs::remove_file(&temporary);
            return Err(cache_error(&path, first_error));
        }
    }
    Ok(())
}
