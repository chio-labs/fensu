//! Archive canonical memory sources and synchronize the generated index.

use std::path::{Path, PathBuf};

use crate::engine::errors::MemoryIndexError;
use crate::engine::helpers::archival::archive;
use crate::engine::models::MemoryArchiveResult;

/// Plan, publish, and synchronize one explicit or age-based archive operation.
pub fn archive_memory(
    repository_root: &Path,
    database_path: &Path,
    requested_paths: &[PathBuf],
    archive_after_days: u64,
    confirmed: bool,
) -> Result<MemoryArchiveResult, MemoryIndexError> {
    archive::archive(
        repository_root,
        database_path,
        requested_paths,
        archive_after_days,
        confirmed,
    )
}
