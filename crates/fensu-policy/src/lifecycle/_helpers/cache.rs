//! Shared cache envelope, paths, and filesystem errors.

use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

use crate::lifecycle::errors::LifecycleError;

#[derive(Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct CacheEnvelope<T> {
    pub(crate) schema: u32,
    pub(crate) identity: String,
    pub(crate) value: T,
}

pub(crate) fn cache_path(root: &Path, namespace: &str) -> PathBuf {
    let digest = Sha256::digest(namespace.as_bytes());
    root.join(format!("{:x}.json", digest))
}

pub(crate) fn cache_error(path: &Path, error: std::io::Error) -> LifecycleError {
    LifecycleError::CacheIo {
        message: format!("{}: {error}", path.display()),
    }
}

pub(crate) fn temporary_cache_path(path: &Path) -> PathBuf {
    let timestamp = match SystemTime::now().duration_since(UNIX_EPOCH) {
        Ok(value) => value.as_nanos(),
        Err(_) => 0,
    };
    let thread = format!("{:?}", std::thread::current().id());
    path.with_extension(format!("{}-{thread}-{timestamp}.tmp", std::process::id()))
}
