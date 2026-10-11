//! Deterministic package discovery and repository-local ignore inputs.

use std::fs;
use std::path::{Path, PathBuf};

pub(crate) fn ignore_files(root: &Path, package: &Path) -> Vec<PathBuf> {
    let boundary = root
        .ancestors()
        .find(|directory| directory.join(".git").exists())
        .unwrap_or(root);
    let mut paths = package
        .ancestors()
        .take_while(|path| path.starts_with(boundary))
        .map(|path| path.join(".gitignore"))
        .collect::<Vec<_>>();
    paths.reverse();
    paths
}

pub(crate) fn ignore_content(path: &Path) -> Result<Option<String>, String> {
    match fs::read_to_string(path) {
        Ok(content) => Ok(Some(content)),
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(None),
        Err(error) => Err(format!(
            "cannot read ignore input {}: {error}",
            path.display()
        )),
    }
}

pub(crate) fn entries(package: &Path) -> Result<Vec<fs::DirEntry>, String> {
    let mut entries = fs::read_dir(package)
        .map_err(|error| format!("cannot list {}: {error}", package.display()))?
        .collect::<Result<Vec<_>, _>>()
        .map_err(|error| format!("cannot list {}: {error}", package.display()))?;
    entries.sort_by_key(fs::DirEntry::file_name);
    entries.retain(|entry| !entry.file_name().to_string_lossy().starts_with('.'));
    Ok(entries)
}

pub(crate) fn matchers(
    root: &Path,
    package: &Path,
) -> Result<Vec<ignore::gitignore::Gitignore>, String> {
    let mut matchers: Vec<ignore::gitignore::Gitignore> = Vec::new();
    for path in ignore_files(root, package) {
        let Some(content) = ignore_content(&path)? else {
            continue;
        };
        let mut builder = ignore::gitignore::GitignoreBuilder::new(path.parent().unwrap_or(root));
        for line in content.trim_start_matches('\u{feff}').lines() {
            builder
                .add_line(Some(path.clone()), line)
                .map_err(|error| error.to_string())?;
        }
        matchers.push(builder.build().map_err(|error| error.to_string())?);
    }
    Ok(matchers)
}

pub(crate) fn ignored(
    path: &Path,
    directory: bool,
    matchers: &[ignore::gitignore::Gitignore],
) -> bool {
    matchers
        .iter()
        .rev()
        .map(|matcher| matcher.matched_path_or_any_parents(path, directory))
        .find(|matched| !matched.is_none())
        .is_some_and(|matched| matched.is_ignore())
}
