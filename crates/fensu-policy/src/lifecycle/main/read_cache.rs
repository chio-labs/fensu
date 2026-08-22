//! Read one reusable cache namespace.

use std::fs;
use std::path::Path;

use serde::de::DeserializeOwned;

use crate::lifecycle::_helpers::cache::{cache_error, cache_path, CacheEnvelope};
use crate::lifecycle::constants::CACHE_SCHEMA_VERSION;
use crate::lifecycle::errors::LifecycleError;
use crate::lifecycle::models::CacheRead;

/// Read one namespace, distinguishing a first miss from stale or malformed data.
pub fn read_cache<T: DeserializeOwned>(
    root: &Path,
    namespace: &str,
    expected_identity: &str,
) -> Result<CacheRead<T>, LifecycleError> {
    let path = cache_path(root, namespace);
    let data = match fs::read(&path) {
        Ok(data) => data,
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => return Ok(CacheRead::Miss),
        Err(error) => return Err(cache_error(&path, error)),
    };
    let envelope = match serde_json::from_slice::<CacheEnvelope<T>>(&data) {
        Ok(value) => value,
        Err(_) => return Ok(CacheRead::Invalidated),
    };
    if envelope.schema != CACHE_SCHEMA_VERSION || envelope.identity != expected_identity {
        return Ok(CacheRead::Invalidated);
    }
    Ok(CacheRead::Hit(envelope.value))
}
