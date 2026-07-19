//! Transactional temporary-database construction and atomic replacement.

use std::ffi::OsString;
use std::fs;
use std::io;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};

use tempfile::TempPath;

use crate::engine::errors::MemoryIndexError;
use crate::engine::helpers::publication::streaming;
use crate::engine::models::{IndexSummary, MemoryDiagnostic};
use crate::source::models::DiscoveryResult;

static TEMPORARY_COUNTER: AtomicU64 = AtomicU64::new(0);

pub(crate) struct PublicationResult {
    pub(crate) summary: IndexSummary,
    pub(crate) diagnostics: Vec<MemoryDiagnostic>,
    pub(crate) published: bool,
}

pub(crate) fn publish_discovery(
    discovery: DiscoveryResult,
    database_path: &Path,
    require_valid: bool,
) -> Result<PublicationResult, MemoryIndexError> {
    let parent = database_parent(database_path)?;
    fs::create_dir_all(&parent).map_err(|error| {
        MemoryIndexError::filesystem("create database directory", parent.clone(), error)
    })?;
    let temporary_path = temporary_path(database_path, &parent)?;
    let journal_path = sidecar_path(&temporary_path, "-journal");
    let wal_path = sidecar_path(&temporary_path, "-wal");
    let shm_path = sidecar_path(&temporary_path, "-shm");
    let temporary_files: [&Path; 4] = [
        temporary_path.as_path(),
        journal_path.as_path(),
        wal_path.as_path(),
        shm_path.as_path(),
    ];
    let result = match streaming::build(discovery, &temporary_path, require_valid) {
        Ok(result) => result,
        Err(error) => return Err(cleanup_files(error, &temporary_files)),
    };
    if !result.published {
        remove_if_exists(&temporary_path).map_err(|error| {
            MemoryIndexError::filesystem("remove invalid memory index", temporary_path, error)
        })?;
        return Ok(result);
    }
    for sidecar in [&journal_path, &wal_path, &shm_path] {
        if let Err(error) = remove_if_exists(sidecar) {
            let failure = MemoryIndexError::filesystem(
                "remove temporary SQLite sidecar",
                sidecar.clone(),
                error,
            );
            return Err(cleanup_files(failure, &temporary_files));
        }
    }
    let temporary = TempPath::try_from_path(&temporary_path).map_err(|error| {
        MemoryIndexError::filesystem(
            "prepare atomic memory index publication",
            temporary_path.clone(),
            error,
        )
    })?;
    if let Err(error) = temporary.persist(database_path) {
        let failure = MemoryIndexError::filesystem(
            "publish memory index",
            database_path.to_path_buf(),
            error.error,
        );
        return Err(cleanup_files(failure, &temporary_files));
    }
    Ok(result)
}

fn database_parent(database_path: &Path) -> Result<PathBuf, MemoryIndexError> {
    if database_path.file_name().is_none() {
        return Err(MemoryIndexError::InvalidDatabasePath(
            database_path.to_path_buf(),
        ));
    }
    let parent = database_path.parent().unwrap_or_else(|| Path::new("."));
    if parent.as_os_str().is_empty() {
        Ok(PathBuf::from("."))
    } else {
        Ok(parent.to_path_buf())
    }
}

fn temporary_path(database_path: &Path, parent: &Path) -> Result<PathBuf, MemoryIndexError> {
    let file_name = database_path
        .file_name()
        .ok_or_else(|| MemoryIndexError::InvalidDatabasePath(database_path.to_path_buf()))?;
    let sequence = TEMPORARY_COUNTER.fetch_add(1, Ordering::Relaxed);
    let mut temporary_name = OsString::from(".");
    temporary_name.push(file_name);
    temporary_name.push(format!(
        ".strata-memory-{}-{sequence}.tmp",
        std::process::id()
    ));
    Ok(parent.join(temporary_name))
}

fn sidecar_path(database_path: &Path, suffix: &str) -> PathBuf {
    let mut value = database_path.as_os_str().to_os_string();
    value.push(suffix);
    PathBuf::from(value)
}

fn cleanup_files(mut original: MemoryIndexError, paths: &[&Path]) -> MemoryIndexError {
    for path in paths {
        if let Err(source) = remove_if_exists(path) {
            original = MemoryIndexError::Cleanup {
                path: path.to_path_buf(),
                source,
                original: Box::new(original),
            };
        }
    }
    original
}

fn remove_if_exists(path: &Path) -> Result<(), io::Error> {
    match fs::remove_file(path) {
        Ok(()) => Ok(()),
        Err(error) if error.kind() == io::ErrorKind::NotFound => Ok(()),
        Err(error) => Err(error),
    }
}
