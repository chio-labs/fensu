//! Survey the repository for existing configuration and Python packages.

use std::collections::BTreeSet;
use std::fs;
use std::path::{Path, PathBuf};

use walkdir::WalkDir;

use crate::configuration::main::load;
use crate::init::_helpers::arguments::requests_scopes;
use crate::init::models::RepositorySurvey;
use crate::models::{CliOutput, InitOptions};

pub(crate) fn survey_repository(repository: &Path) -> RepositorySurvey {
    let python_files = repository_python_files(repository);
    let package_roots = detected_roots(repository);
    let empty = package_roots.is_empty() && python_files.is_empty();
    RepositorySurvey {
        package_roots,
        empty,
    }
}

pub(crate) fn local_config(repository: &Path) -> Option<PathBuf> {
    let fensu = repository.join("fensu.toml");
    if fensu.is_file() {
        return Some(fensu);
    }
    let pyproject = repository.join("pyproject.toml");
    let Ok(text) = fs::read_to_string(&pyproject) else {
        return None;
    };
    text.contains("[tool.fensu]").then_some(pyproject)
}

pub(crate) fn existing_configuration(
    repository: &Path,
    path: &Path,
    options: &InitOptions,
) -> Result<CliOutput, String> {
    if let Err(error) = load::load(repository) {
        return Err(format!(
            "Fensu configuration already exists but is not usable: {}\n{error}\nEdit that file, \
             or delete it and rerun fensu init.",
            path.display()
        ));
    }
    if requests_scopes(options) {
        return Err(format!(
            "Fensu configuration already exists: {}\nRefusing to overwrite it, so --root, \
             --tests, --tooling, and --name were not applied. Edit that file, or delete it and \
             rerun fensu init.",
            path.display()
        ));
    }
    Ok(CliOutput::success(format!(
        "Fensu configuration already exists: {} (nothing to do)\n",
        path.display()
    )))
}

fn repository_python_files(repository: &Path) -> Vec<PathBuf> {
    WalkDir::new(repository)
        .into_iter()
        .filter_entry(|entry| {
            !matches!(
                entry.file_name().to_str(),
                Some(".git" | ".venv" | "venv" | "target" | "dist" | "build" | "__pycache__")
            )
        })
        .filter_map(Result::ok)
        .filter(|entry| {
            entry.file_type().is_file()
                && entry.path().extension().and_then(|value| value.to_str()) == Some("py")
        })
        .map(|entry| entry.into_path())
        .collect()
}

fn detected_roots(repository: &Path) -> Vec<String> {
    let mut candidates: BTreeSet<String> = BTreeSet::new();
    for path in repository_python_files(repository) {
        if path.file_name().and_then(|value| value.to_str()) != Some("__init__.py") {
            continue;
        }
        let Some(parent) = path.parent() else {
            continue;
        };
        let parent_parent_is_package = parent
            .parent()
            .is_some_and(|candidate| candidate.join("__init__.py").is_file());
        if !parent_parent_is_package {
            if let Ok(relative) = parent.strip_prefix(repository) {
                candidates.insert(relative.to_string_lossy().replace('\\', "/"));
            }
        }
    }
    let detected = candidates.into_iter().collect::<Vec<_>>();
    let mut roots: Vec<String> = Vec::new();
    for candidate in &detected {
        if !detected
            .iter()
            .any(|ancestor| is_nested_within(candidate, ancestor))
        {
            roots.push(candidate.clone());
        }
    }
    roots
}

fn is_nested_within(candidate: &str, ancestor: &str) -> bool {
    candidate.len() > ancestor.len() && candidate.starts_with(&format!("{ancestor}/"))
}

pub(crate) fn python_count(path: &Path) -> usize {
    WalkDir::new(path)
        .into_iter()
        .filter_map(Result::ok)
        .filter(|entry| {
            entry.file_type().is_file()
                && entry.path().extension().and_then(|value| value.to_str()) == Some("py")
        })
        .count()
}
