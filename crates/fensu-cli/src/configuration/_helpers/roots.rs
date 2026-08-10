use std::ffi::OsString;
use std::path::{Component, Path, PathBuf};

use crate::repository_io::main::relative_path::relative_path;

pub(crate) fn normalize_target_root(name: &str, value: &str) -> Result<String, String> {
    let bytes = value.as_bytes();
    let windows_absolute = value.starts_with('\\')
        || bytes.get(1) == Some(&b':') && bytes.first().is_some_and(u8::is_ascii_alphabetic);
    let portable = value.replace('\\', "/");
    let configured = Path::new(&portable);
    if configured.is_absolute() || windows_absolute {
        return Err(format!(
            "Target {name} root '{value}' must be repository-relative."
        ));
    }
    let mut normalized = PathBuf::new();
    for component in configured.components() {
        match component {
            Component::CurDir => {}
            Component::ParentDir if normalized.pop() => {}
            Component::ParentDir => {
                return Err(format!(
                    "Target {name} root '{value}' must not escape the repository."
                ));
            }
            Component::Normal(part) => normalized.push(part),
            Component::RootDir | Component::Prefix(_) => {
                return Err(format!(
                    "Target {name} root '{value}' must be repository-relative."
                ));
            }
        }
    }
    Ok(if normalized.as_os_str().is_empty() {
        ".".to_owned()
    } else {
        normalized.to_string_lossy().replace('\\', "/")
    })
}

pub(crate) fn resolve_target_root(
    repository_root: &Path,
    configured: &str,
) -> Result<PathBuf, String> {
    let repository = dunce::canonicalize(repository_root).map_err(|error| {
        format!(
            "Could not resolve repository root {}: {error}",
            repository_root.display()
        )
    })?;
    let candidate = repository.join(configured);
    let resolved = canonicalize_with_missing_suffix(&candidate)?;
    if relative_path(&resolved, &repository).is_none() {
        return Err(format!(
            "Target root '{configured}' must not escape the repository."
        ));
    }
    Ok(resolved)
}

fn canonicalize_with_missing_suffix(path: &Path) -> Result<PathBuf, String> {
    let mut ancestor = path.to_path_buf();
    let mut suffix: Vec<OsString> = Vec::new();
    loop {
        match dunce::canonicalize(&ancestor) {
            Ok(mut resolved) => {
                for component in suffix.iter().rev() {
                    resolved.push(component);
                }
                return Ok(resolved);
            }
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => {
                let component = ancestor.file_name().ok_or_else(|| {
                    format!("Could not resolve target root {}: {error}", path.display())
                })?;
                suffix.push(component.to_os_string());
                ancestor = ancestor.parent().map(Path::to_path_buf).ok_or_else(|| {
                    format!("Could not resolve target root {}: {error}", path.display())
                })?;
            }
            Err(error) => {
                return Err(format!(
                    "Could not resolve target root {}: {error}",
                    path.display()
                ));
            }
        }
    }
}

pub(crate) fn validate_nested_roots(roots: Vec<String>) -> Result<(), String> {
    for (index, first) in roots.iter().enumerate() {
        let first_parts = first.split('/').collect::<Vec<_>>();
        for second in roots.iter().skip(index + 1) {
            let second_parts = second.split('/').collect::<Vec<_>>();
            let length = first_parts.len().min(second_parts.len());
            if first_parts[..length] != second_parts[..length] {
                continue;
            }
            return Err(nested_roots_error(
                first,
                second,
                first_parts.len() <= second_parts.len(),
            ));
        }
    }
    Ok(())
}

fn nested_roots_error(first: &str, second: &str, first_is_outer: bool) -> String {
    let (outer, inner) = if first_is_outer {
        (first, second)
    } else {
        (second, first)
    };
    if outer == inner {
        return format!("Config key roots must not contain duplicate paths: {outer:?}.");
    }
    format!("Config key roots must not contain nested paths: {outer:?} contains {inner:?}.")
}
