//! Filesystem reads and portable path normalization for source discovery.

use std::fs::{self, DirEntry, FileType};
use std::path::{Component, Path};
use std::time::SystemTime;
#[cfg(unix)]
use std::time::{Duration, UNIX_EPOCH};

use sha2::{Digest, Sha256};

use crate::source::models::{DiscoveryDiagnostic, SourceMetadata};
use crate::source::types::DiagnosticKind;

pub(crate) fn sorted_directory_entries(
    repository_root: &Path,
    directory: &Path,
    diagnostics: &mut Vec<DiscoveryDiagnostic>,
) -> Vec<DirEntry> {
    let metadata = match fs::symlink_metadata(directory) {
        Ok(metadata) => metadata,
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => return Vec::new(),
        Err(error) => {
            diagnostics.push(diagnostic(
                repository_root,
                directory,
                DiagnosticKind::Io,
                format!("cannot inspect directory: {error}"),
            ));
            return Vec::new();
        }
    };
    if metadata.file_type().is_symlink() {
        diagnostics.push(diagnostic(
            repository_root,
            directory,
            DiagnosticKind::SymlinkRejected,
            "canonical directory is a symlink".to_owned(),
        ));
        return Vec::new();
    }
    if !metadata.is_dir() {
        diagnostics.push(diagnostic(
            repository_root,
            directory,
            DiagnosticKind::UnsupportedFileType,
            "canonical directory path is not a directory".to_owned(),
        ));
        return Vec::new();
    }
    let reader = match fs::read_dir(directory) {
        Ok(reader) => reader,
        Err(error) => {
            diagnostics.push(diagnostic(
                repository_root,
                directory,
                DiagnosticKind::Io,
                format!("cannot read directory: {error}"),
            ));
            return Vec::new();
        }
    };
    let mut entries: Vec<DirEntry> = Vec::new();
    for result in reader {
        match result {
            Ok(entry) => entries.push(entry),
            Err(error) => diagnostics.push(diagnostic(
                repository_root,
                directory,
                DiagnosticKind::Io,
                format!("cannot inspect directory entry: {error}"),
            )),
        }
    }
    entries.sort_by_key(|entry| entry.file_name().to_string_lossy().into_owned());
    entries
}

pub(crate) fn entry_type(
    repository_root: &Path,
    entry: &DirEntry,
    diagnostics: &mut Vec<DiscoveryDiagnostic>,
) -> Option<FileType> {
    match entry.file_type() {
        Ok(file_type) => Some(file_type),
        Err(error) => {
            diagnostics.push(diagnostic(
                repository_root,
                &entry.path(),
                DiagnosticKind::Io,
                format!("cannot classify directory entry: {error}"),
            ));
            None
        }
    }
}

pub(crate) fn entry_name(
    repository_root: &Path,
    entry: &DirEntry,
    diagnostics: &mut Vec<DiscoveryDiagnostic>,
) -> Option<String> {
    match entry.file_name().into_string() {
        Ok(name) => Some(name),
        Err(_) => {
            diagnostics.push(diagnostic(
                repository_root,
                &entry.path(),
                DiagnosticKind::InvalidPathEncoding,
                "canonical path component is not UTF-8".to_owned(),
            ));
            None
        }
    }
}

pub(crate) fn source_metadata(path: &Path) -> Result<SourceMetadata, String> {
    let metadata = fs::symlink_metadata(path).map_err(|error| error.to_string())?;
    if metadata.file_type().is_symlink() {
        return Err("source became a symlink while it was being read".to_owned());
    }
    if !metadata.is_file() {
        return Err("source is not a regular file".to_owned());
    }
    let bytes = fs::read(path).map_err(|error| error.to_string())?;
    let modified_at = metadata.modified().map_err(|error| error.to_string())?;
    Ok(SourceMetadata {
        content_sha256: hex::encode(Sha256::digest(&bytes)),
        byte_size: bytes.len() as u64,
        modified_at,
        changed_at: changed_at(&metadata),
    })
}

pub(crate) fn portable_path(repository_root: &Path, path: &Path) -> Result<String, String> {
    let relative = path
        .strip_prefix(repository_root)
        .map_err(|error| error.to_string())?;
    let mut parts: Vec<&str> = Vec::new();
    for component in relative.components() {
        match component {
            Component::Normal(value) => parts.push(
                value
                    .to_str()
                    .ok_or_else(|| "path component is not UTF-8".to_owned())?,
            ),
            _ => return Err("path is not repository-relative".to_owned()),
        }
    }
    Ok(parts.join("/"))
}

pub(crate) fn diagnostic(
    repository_root: &Path,
    path: &Path,
    kind: DiagnosticKind,
    message: String,
) -> DiscoveryDiagnostic {
    DiscoveryDiagnostic {
        kind,
        repository_relative_path: diagnostic_path(repository_root, path),
        message,
    }
}

fn diagnostic_path(repository_root: &Path, path: &Path) -> String {
    match portable_path(repository_root, path) {
        Ok(relative) => relative,
        Err(_) => path.to_string_lossy().into_owned(),
    }
}

#[cfg(unix)]
fn changed_at(metadata: &fs::Metadata) -> Option<SystemTime> {
    use std::os::unix::fs::MetadataExt;

    signed_unix_time(metadata.ctime(), metadata.ctime_nsec())
}

#[cfg(not(unix))]
fn changed_at(_metadata: &fs::Metadata) -> Option<SystemTime> {
    None
}

#[cfg(unix)]
fn signed_unix_time(seconds: i64, nanoseconds: i64) -> Option<SystemTime> {
    let nanos = u64::try_from(nanoseconds).ok()?;
    if seconds >= 0 {
        return UNIX_EPOCH
            .checked_add(Duration::from_secs(seconds as u64))?
            .checked_add(Duration::from_nanos(nanos));
    }
    UNIX_EPOCH
        .checked_sub(Duration::from_secs(seconds.unsigned_abs()))?
        .checked_add(Duration::from_nanos(nanos))
}
