use std::path::{Path, PathBuf};

pub(crate) fn relative_path(path: &Path, root: &Path) -> Option<PathBuf> {
    let path = normalize_lexical(path)?;
    let root = normalize_lexical(root)?;
    if let Ok(relative) = path.strip_prefix(&root) {
        return Some(relative.to_path_buf());
    }
    let path_parts = windows_components(path.to_str()?)?;
    let root_parts = windows_components(root.to_str()?)?;
    if path_parts.len() < root_parts.len()
        || !path_parts
            .iter()
            .zip(&root_parts)
            .all(|(part, root)| part == root)
    {
        return None;
    }
    Some(path_parts[root_parts.len()..].iter().collect())
}

fn normalize_lexical(path: &Path) -> Option<PathBuf> {
    let mut normalized = PathBuf::new();
    for component in path.components() {
        match component {
            std::path::Component::CurDir => {}
            std::path::Component::ParentDir => return None,
            value => normalized.push(value.as_os_str()),
        }
    }
    Some(normalized)
}

fn windows_components(value: &str) -> Option<Vec<String>> {
    let portable = value.replace('\\', "/");
    let stripped = if portable
        .get(..8)
        .is_some_and(|prefix| prefix.eq_ignore_ascii_case("//?/UNC/"))
    {
        format!("//{}", &portable[8..])
    } else {
        portable
            .strip_prefix("//?/")
            .map_or(portable.clone(), str::to_owned)
    };
    let mut parts: Vec<String> = Vec::new();
    let remainder = if let Some(unc) = stripped.strip_prefix("//") {
        parts.push("//".to_owned());
        unc
    } else if stripped.as_bytes().get(1) == Some(&b':')
        && stripped
            .as_bytes()
            .first()
            .is_some_and(u8::is_ascii_alphabetic)
        && stripped
            .as_bytes()
            .get(2)
            .is_none_or(|value| *value == b'/')
    {
        ""
    } else {
        return None;
    };
    let values = if remainder.is_empty() {
        stripped.split('/')
    } else {
        remainder.split('/')
    };
    for part in values.filter(|part| !part.is_empty()) {
        if matches!(part, "." | "..") {
            return None;
        }
        parts.push(part.to_owned());
    }
    (!parts.is_empty()).then_some(parts)
}
