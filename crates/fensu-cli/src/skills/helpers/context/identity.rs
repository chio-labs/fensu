use std::env;
use std::fs;
use std::path::{Component, Path, PathBuf};

use unicode_normalization::UnicodeNormalization;

use crate::models::Config;

const GIT_INSTALL_ROOT: &str = "git";
const HOME_PATH: &str = "~";
const PROJECT_INSTALL_ROOT: &str = "project";

pub(crate) fn find_git_root(project_root: &Path) -> Option<PathBuf> {
    project_root
        .ancestors()
        .find(|candidate| {
            let marker = candidate.join(".git");
            marker.is_dir() || marker.is_file()
        })
        .map(Path::to_path_buf)
}

pub(crate) fn resolve_install_root(
    value: Option<&str>,
    project_root: &Path,
    invocation: &Path,
    git_root: Option<&Path>,
) -> Result<PathBuf, String> {
    match value {
        None => Ok(git_root.unwrap_or(project_root).to_path_buf()),
        Some(PROJECT_INSTALL_ROOT) => Ok(project_root.to_path_buf()),
        Some(GIT_INSTALL_ROOT) => git_root.map(Path::to_path_buf).ok_or_else(|| {
            "--install-root git requires a parent Git repository containing .git.".to_owned()
        }),
        Some(path) => {
            let expanded = if path == HOME_PATH || path.starts_with("~/") {
                let home = home_dir()?;
                home.join(path.trim_start_matches('~').trim_start_matches('/'))
            } else {
                PathBuf::from(path)
            };
            Ok(normalize_absolute(if expanded.is_absolute() {
                expanded
            } else {
                invocation.join(expanded)
            }))
        }
    }
}

pub(crate) fn normalize_absolute(path: PathBuf) -> PathBuf {
    let mut result = PathBuf::new();
    for component in path.components() {
        match component {
            Component::ParentDir => {
                let _ = result.pop();
            }
            Component::CurDir => {}
            _ => result.push(component.as_os_str()),
        }
    }
    result
}

pub(crate) fn home_dir() -> Result<PathBuf, String> {
    env::var_os("HOME")
        .or_else(|| env::var_os("USERPROFILE"))
        .map(PathBuf::from)
        .ok_or_else(|| {
            "Could not resolve the home directory for global skill installation.".to_owned()
        })
}

pub(crate) fn resolve_identity(
    config: &Config,
    config_path: &Path,
    project_root: &Path,
    git_root: Option<&Path>,
) -> Result<String, String> {
    if let Some(value) = &config.skills_name {
        return Ok(format!("fensu-{}", normalize_identity(value)?));
    }
    if let Some(value) = nearest_project_name(project_root)? {
        if let Ok(normalized) = normalize_identity(&value) {
            return Ok(format!("fensu-{normalized}"));
        }
    }
    if let Some(value) = config_path
        .parent()
        .and_then(Path::file_name)
        .and_then(|item| item.to_str())
    {
        if let Ok(normalized) = normalize_identity(value) {
            return Ok(format!("fensu-{normalized}"));
        }
    }
    let fallback = git_root
        .and_then(|root| project_root.strip_prefix(root).ok())
        .filter(|path| !path.as_os_str().is_empty())
        .unwrap_or(project_root)
        .to_string_lossy();
    Ok(format!("fensu-{}", normalize_identity(&fallback)?))
}

fn normalize_identity(value: &str) -> Result<String, String> {
    let decomposed = value
        .nfkd()
        .filter(char::is_ascii)
        .collect::<String>()
        .to_lowercase();
    let mut output = String::new();
    for character in decomposed.chars() {
        if character.is_ascii_alphanumeric() {
            output.push(character);
        } else if !output.is_empty() && !output.ends_with('-') {
            output.push('-');
        }
    }
    let output = output.trim_matches('-').to_owned();
    if output.is_empty() {
        return Err(format!(
            "Skill identity {value:?} does not contain an ASCII letter or digit."
        ));
    }
    Ok(output)
}

fn nearest_project_name(project_root: &Path) -> Result<Option<String>, String> {
    for directory in project_root.ancestors() {
        let path = directory.join("pyproject.toml");
        if !path.is_file() {
            continue;
        }
        let bytes = fs::read(&path).map_err(|error| error.to_string())?;
        let value = toml::from_slice::<toml::Value>(&bytes).map_err(|error| {
            format!(
                "Could not parse {} while resolving skill identity: {error}",
                path.display()
            )
        })?;
        if let Some(name) = value
            .get("project")
            .and_then(|project| project.get("name"))
            .and_then(toml::Value::as_str)
            .filter(|name| !name.is_empty())
        {
            return Ok(Some(name.to_owned()));
        }
    }
    Ok(None)
}
