//! Repository path resolution and relative identity helpers.

use std::ffi::OsString;
use std::path::{Path, PathBuf};

pub(crate) fn resolve_allow_missing(path: &Path) -> Option<PathBuf> {
    let mut candidate = path.to_path_buf();
    let mut missing_parts: Vec<OsString> = Vec::new();
    loop {
        if let Ok(mut resolved) = dunce::canonicalize(&candidate) {
            for part in missing_parts.iter().rev() {
                resolved.push(part);
            }
            return Some(resolved);
        }
        if candidate
            .symlink_metadata()
            .is_ok_and(|metadata| metadata.file_type().is_symlink())
        {
            return None;
        }
        missing_parts.push(candidate.file_name()?.to_os_string());
        candidate = candidate.parent()?.to_path_buf();
    }
}

pub(crate) fn repository_relative_value(repo_root: &Path, path: &Path) -> Option<String> {
    let relative = path.strip_prefix(repo_root).ok()?;
    if relative.as_os_str().is_empty() {
        return Some(".".to_owned());
    }
    let parts: Option<Vec<&str>> = relative.iter().map(|part| part.to_str()).collect();
    Some(parts?.join("/"))
}
