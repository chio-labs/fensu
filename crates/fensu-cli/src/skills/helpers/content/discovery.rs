use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};

use crate::skills::models::{ProjectSkillBundle, ProjectSkillFile, SkillContext};

const RESERVED_DEVICE_NAME_LENGTH: usize = 4;

pub(crate) fn discover_project_skills(
    context: &SkillContext,
) -> Result<Vec<ProjectSkillBundle>, String> {
    let mut root = context.project_root.clone();
    for part in [".ai", "knowledge", "repo", "skills"] {
        root.push(part);
        match fs::symlink_metadata(&root) {
            Ok(metadata) if metadata.file_type().is_symlink() || !metadata.is_dir() => {
                return Err(format!(
                    "refusing unsafe project skills source: {}",
                    root.display()
                ))
            }
            Ok(_) => {}
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => return Ok(Vec::new()),
            Err(error) => return Err(error.to_string()),
        }
    }
    let mut entries = read_sorted(&root)?;
    let mut identities = HashMap::new();
    let mut bundles = Vec::new();
    for entry in entries.drain(..) {
        let metadata = fs::symlink_metadata(&entry).map_err(|error| error.to_string())?;
        if metadata.file_type().is_symlink() || !metadata.is_dir() {
            return Err(format!(
                "project skill entry must be a regular directory: {}",
                entry.display()
            ));
        }
        let identity = entry
            .file_name()
            .and_then(|name| name.to_str())
            .ok_or_else(|| {
                format!(
                    "project skill name must be portable ASCII kebab-case: {}",
                    entry.display()
                )
            })?
            .to_owned();
        validate_identity(&identity, &entry)?;
        let normalized = identity.to_ascii_lowercase();
        if normalized == context.identity.to_ascii_lowercase() {
            return Err(format!(
                "duplicate normalized skill identity {identity:?} conflicts with generated guidance"
            ));
        }
        if let Some(previous) = identities.insert(normalized, entry.clone()) {
            return Err(format!(
                "duplicate normalized project skill identity: {} and {}",
                previous.display(),
                entry.display()
            ));
        }
        let files = discover_files(&entry)?;
        let document = files
            .iter()
            .find(|file| file.relative_path == Path::new("SKILL.md"))
            .ok_or_else(|| {
                format!(
                    "project skill bundle has no regular SKILL.md: {}",
                    entry.display()
                )
            })?;
        if std::str::from_utf8(&document.content).is_err() {
            return Err(format!(
                "project skill SKILL.md is not UTF-8: {}",
                entry.display()
            ));
        }
        if document.content.split(|byte| *byte == b'\n').any(|line| {
            let line = line.strip_suffix(b"\r").unwrap_or(line);
            line == b"<!-- synchronized-project-skill-by: fensu skills -->"
                || line.starts_with(b"<!-- fensu-skill-owner: ")
        }) {
            return Err(format!(
                "canonical project skill contains reserved ownership metadata: {}",
                entry.display()
            ));
        }
        bundles.push(ProjectSkillBundle { identity, files });
    }
    Ok(bundles)
}

fn validate_identity(identity: &str, path: &Path) -> Result<(), String> {
    let valid = identity.bytes().enumerate().all(|(index, byte)| {
        byte.is_ascii_lowercase()
            || byte.is_ascii_digit() && index > 0
            || byte == b'-' && index > 0 && index + 1 < identity.len()
    }) && identity
        .as_bytes()
        .first()
        .is_some_and(u8::is_ascii_lowercase)
        && !identity.contains("--");
    let reserved = matches!(identity, "con" | "prn" | "aux" | "nul")
        || ((identity.starts_with("com") || identity.starts_with("lpt"))
            && identity.len() == RESERVED_DEVICE_NAME_LENGTH
            && identity.as_bytes()[3].is_ascii_digit()
            && identity.as_bytes()[3] != b'0');
    if !valid || reserved {
        return Err(format!(
            "project skill name must be portable ASCII kebab-case: {}",
            path.display()
        ));
    }
    Ok(())
}

fn discover_files(root: &Path) -> Result<Vec<ProjectSkillFile>, String> {
    let mut pending = vec![root.to_path_buf()];
    let mut normalized = HashMap::<String, PathBuf>::new();
    let mut files = Vec::new();
    while let Some(directory) = pending.pop() {
        let mut entries = read_sorted(&directory)?;
        entries.reverse();
        for entry in entries {
            let relative = entry
                .strip_prefix(root)
                .map_err(|error| error.to_string())?
                .to_path_buf();
            let portable = relative.to_str().ok_or_else(|| {
                format!("project skill path is not valid UTF-8: {}", entry.display())
            })?;
            let key = portable.replace('\\', "/").to_lowercase();
            if let Some(previous) = normalized.insert(key, entry.clone()) {
                return Err(format!(
                    "project skill bundle has a case-folding path collision: {} and {}",
                    previous.display(),
                    entry.display()
                ));
            }
            let before = fs::symlink_metadata(&entry).map_err(|error| error.to_string())?;
            if before.file_type().is_symlink() {
                return Err(format!(
                    "project skill content cannot be a symlink: {}",
                    entry.display()
                ));
            }
            if before.is_dir() {
                pending.push(entry);
                continue;
            }
            if !before.is_file() {
                return Err(format!(
                    "project skill content must be a regular file: {}",
                    entry.display()
                ));
            }
            let content = fs::read(&entry).map_err(|error| error.to_string())?;
            let after = fs::symlink_metadata(&entry).map_err(|error| error.to_string())?;
            if !same_file_state(&before, &after) || !after.is_file() {
                return Err(format!(
                    "project skill content changed during discovery: {}",
                    entry.display()
                ));
            }
            files.push(ProjectSkillFile {
                relative_path: relative,
                content,
                mode: file_mode(&after),
            });
        }
    }
    files.sort_by(|left, right| left.relative_path.cmp(&right.relative_path));
    Ok(files)
}

fn read_sorted(path: &Path) -> Result<Vec<PathBuf>, String> {
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
fn same_file_state(left: &fs::Metadata, right: &fs::Metadata) -> bool {
    use std::os::unix::fs::MetadataExt;
    (
        left.dev(),
        left.ino(),
        left.mode(),
        left.len(),
        left.mtime_nsec(),
        left.ctime_nsec(),
    ) == (
        right.dev(),
        right.ino(),
        right.mode(),
        right.len(),
        right.mtime_nsec(),
        right.ctime_nsec(),
    )
}

#[cfg(not(unix))]
fn same_file_state(left: &fs::Metadata, right: &fs::Metadata) -> bool {
    left.len() == right.len()
        && left.modified().ok() == right.modified().ok()
        && left.permissions().readonly() == right.permissions().readonly()
}
