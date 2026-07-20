use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct Snapshot {
    pub(crate) path: PathBuf,
    pub(crate) content: Option<Vec<u8>>,
    pub(crate) mode: Option<u32>,
    pub(crate) identity: Option<FileIdentity>,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct FileIdentity {
    device: u64,
    inode: u64,
    length: u64,
    modified: Option<std::time::SystemTime>,
}

pub(crate) fn capture_bundle(root: &Path) -> Result<Vec<Snapshot>, String> {
    if !root.exists() {
        if fs::symlink_metadata(root).is_ok() {
            return Err(format!(
                "refusing to write unsafe skill target: {}",
                root.display()
            ));
        }
        ensure_safe_ancestors(root)?;
        return Ok(Vec::new());
    }
    ensure_safe_directory(root)?;
    let mut pending = vec![root.to_path_buf()];
    let mut normalized = HashMap::<String, PathBuf>::new();
    let mut snapshots = Vec::new();
    while let Some(directory) = pending.pop() {
        let mut entries = sorted_entries(&directory)?;
        entries.reverse();
        for entry in entries {
            let relative = entry
                .strip_prefix(root)
                .map_err(|error| error.to_string())?;
            let key = relative.to_string_lossy().replace('\\', "/").to_lowercase();
            if let Some(previous) = normalized.insert(key, entry.clone()) {
                return Err(format!(
                    "skill bundle path normalization collides: {} and {}",
                    previous.display(),
                    entry.display()
                ));
            }
            let metadata = fs::symlink_metadata(&entry).map_err(|error| error.to_string())?;
            if metadata.file_type().is_symlink() {
                return Err(format!(
                    "refusing to write unsafe skill target: {}",
                    entry.display()
                ));
            }
            if metadata.is_dir() {
                pending.push(entry);
            } else if metadata.is_file() {
                snapshots.push(capture(&entry)?);
            } else {
                return Err(format!(
                    "refusing to write unsafe skill target: {}",
                    entry.display()
                ));
            }
        }
    }
    snapshots.sort_by(|left, right| left.path.cmp(&right.path));
    Ok(snapshots)
}

pub(crate) fn capture(path: &Path) -> Result<Snapshot, String> {
    ensure_safe_ancestors(path)?;
    let before = match fs::symlink_metadata(path) {
        Ok(metadata) => metadata,
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => {
            return Ok(Snapshot {
                path: path.to_path_buf(),
                content: None,
                mode: None,
                identity: None,
            })
        }
        Err(error) => return Err(error.to_string()),
    };
    if before.file_type().is_symlink() || !before.is_file() {
        return Err(format!(
            "refusing to write unsafe skill target: {}",
            path.display()
        ));
    }
    let content = fs::read(path).map_err(|error| error.to_string())?;
    let after = fs::symlink_metadata(path).map_err(|error| error.to_string())?;
    let left = file_identity(&before);
    let right = file_identity(&after);
    if left != right || !after.is_file() {
        return Err(format!(
            "skill target changed during update: {}",
            path.display()
        ));
    }
    Ok(Snapshot {
        path: path.to_path_buf(),
        content: Some(content),
        mode: Some(file_mode(&after)),
        identity: Some(right),
    })
}

pub(crate) fn ensure_snapshot(expected: &Snapshot) -> Result<(), String> {
    let current = capture(&expected.path)?;
    if &current != expected {
        return Err(format!(
            "skill target changed during update: {}",
            expected.path.display()
        ));
    }
    Ok(())
}

pub(crate) fn safe_read(path: &Path) -> Result<Option<Vec<u8>>, String> {
    Ok(capture(path)?.content)
}

fn ensure_safe_ancestors(path: &Path) -> Result<(), String> {
    for parent in path.ancestors().skip(1) {
        match fs::symlink_metadata(parent) {
            Ok(metadata) if metadata.file_type().is_symlink() || !metadata.is_dir() => {
                return Err(format!(
                    "refusing to write unsafe skill target: {}",
                    path.display()
                ))
            }
            Ok(_) => {}
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => {}
            Err(error) => return Err(error.to_string()),
        }
    }
    Ok(())
}

pub(crate) fn ensure_safe_directory(path: &Path) -> Result<(), String> {
    ensure_safe_ancestors(path)?;
    let metadata = fs::symlink_metadata(path).map_err(|error| error.to_string())?;
    if metadata.file_type().is_symlink() || !metadata.is_dir() {
        return Err(format!(
            "refusing to write unsafe skill target: {}",
            path.display()
        ));
    }
    Ok(())
}

pub(crate) fn create_safe_parents(path: &Path, created: &mut Vec<PathBuf>) -> Result<(), String> {
    ensure_safe_ancestors(path)?;
    let mut missing = Vec::new();
    for candidate in path.ancestors() {
        if candidate.exists() {
            break;
        }
        missing.push(candidate.to_path_buf());
    }
    for directory in missing.into_iter().rev() {
        fs::create_dir(&directory)
            .map_err(|error| format!("failed to install skill files: {error}"))?;
        created.push(directory);
    }
    ensure_safe_directory(path)
}

pub(crate) fn normalization_collision(path: &Path) -> Result<Option<PathBuf>, String> {
    let skill = path
        .parent()
        .ok_or_else(|| "Skill target has no parent.".to_owned())?;
    let skills = skill
        .parent()
        .ok_or_else(|| "Skill target has no skills directory.".to_owned())?;
    if !skills.is_dir() {
        return Ok(None);
    }
    let name = skill
        .file_name()
        .and_then(|value| value.to_str())
        .unwrap_or_default();
    Ok(sorted_entries(skills)?.into_iter().find(|entry| {
        let candidate = entry
            .file_name()
            .and_then(|value| value.to_str())
            .unwrap_or_default();
        candidate != name && candidate.to_lowercase() == name.to_lowercase()
    }))
}

pub(crate) fn sorted_entries(path: &Path) -> Result<Vec<PathBuf>, String> {
    let mut entries = fs::read_dir(path)
        .map_err(|error| error.to_string())?
        .map(|entry| {
            entry
                .map(|item| item.path())
                .map_err(|error| error.to_string())
        })
        .collect::<Result<Vec<_>, _>>()?;
    entries.sort();
    Ok(entries)
}

#[cfg(unix)]
fn file_identity(metadata: &fs::Metadata) -> FileIdentity {
    use std::os::unix::fs::MetadataExt;
    FileIdentity {
        device: metadata.dev(),
        inode: metadata.ino(),
        length: metadata.len(),
        modified: metadata.modified().ok(),
    }
}

#[cfg(not(unix))]
fn file_identity(metadata: &fs::Metadata) -> FileIdentity {
    FileIdentity {
        device: 0,
        inode: 0,
        length: metadata.len(),
        modified: metadata.modified().ok(),
    }
}

#[cfg(unix)]
fn file_mode(metadata: &fs::Metadata) -> u32 {
    use std::os::unix::fs::PermissionsExt;
    metadata.permissions().mode() & 0o7777
}

#[cfg(not(unix))]
fn file_mode(metadata: &fs::Metadata) -> u32 {
    if metadata.permissions().readonly() {
        0o444
    } else {
        0o666
    }
}

#[cfg(unix)]
pub(crate) fn set_mode(path: &Path, mode: Option<u32>) -> Result<(), String> {
    use std::os::unix::fs::PermissionsExt;
    if let Some(mode) = mode {
        fs::set_permissions(path, fs::Permissions::from_mode(mode))
            .map_err(|error| error.to_string())?;
    }
    Ok(())
}

#[cfg(not(unix))]
pub(crate) fn set_mode(path: &Path, mode: Option<u32>) -> Result<(), String> {
    if let Some(mode) = mode {
        let mut permissions = fs::metadata(path)
            .map_err(|error| error.to_string())?
            .permissions();
        permissions.set_readonly(mode & 0o222 == 0);
        fs::set_permissions(path, permissions).map_err(|error| error.to_string())?;
    }
    Ok(())
}
