//! Survey the repository for existing Python and SvelteKit targets.

use std::collections::BTreeSet;
use std::fs;
use std::path::{Path, PathBuf};

use walkdir::WalkDir;

use crate::analyzer::AnalyzerId;
use crate::configuration::main::validate_document::validate_document;
use crate::constants::CONFIG_PYPROJECT_FILE;
use crate::init::_helpers::arguments::requests_scopes;
use crate::init::constants::{
    DEFAULT_TARGET_ROOT, PYTHON_TARGET_NAME, TESTS_ROOT, WEB_TARGET_NAME,
};
use crate::init::models::RepositorySurvey;
use crate::models::{CliOutput, DetectedTarget, InitOptions, TestLayout};
use crate::repository_io::main::open_repository::open_repository;
use crate::repository_io::main::read_optional::read_optional;

pub(crate) fn survey_repository(repository: &Path) -> RepositorySurvey {
    let python_files = repository_python_files(repository);
    let package_roots = detected_roots(repository);
    let mut targets = detected_sveltekit_targets(repository);
    let empty = package_roots.is_empty() && python_files.is_empty() && targets.is_empty();
    assign_target_names(
        &mut targets,
        package_roots.iter().any(|root| root != TESTS_ROOT),
    );
    RepositorySurvey {
        package_roots,
        targets,
        empty,
    }
}

fn detected_sveltekit_targets(repository: &Path) -> Vec<DetectedTarget> {
    let mut roots = WalkDir::new(repository)
        .into_iter()
        .filter_entry(|entry| !ignored_web_directory(entry.file_name().to_str()))
        .filter_map(Result::ok)
        .filter(|entry| entry.file_type().is_file() && is_svelte_config(entry.path()))
        .filter_map(|entry| entry.path().parent().map(Path::to_path_buf))
        .filter(|root| valid_sveltekit_root(repository, root))
        .collect::<Vec<_>>();
    roots.sort();
    roots.dedup();
    roots
        .into_iter()
        .filter_map(|root| detected_sveltekit_target(repository, &root))
        .collect()
}

fn detected_sveltekit_target(repository: &Path, root: &Path) -> Option<DetectedTarget> {
    let relative = match root.strip_prefix(repository) {
        Ok(relative) => relative,
        Err(_) => return None,
    };
    let target_root = if relative.as_os_str().is_empty() {
        DEFAULT_TARGET_ROOT.to_owned()
    } else {
        relative.to_string_lossy().replace('\\', "/")
    };
    let tests = if regular_directory(&root.join(TESTS_ROOT)) {
        vec![TESTS_ROOT.to_owned()]
    } else {
        Vec::new()
    };
    Some(DetectedTarget {
        name: target_name(&target_root),
        analyzer: AnalyzerId::Svelte,
        root: target_root,
        roots: vec!["src".to_owned()],
        tests,
        tooling: Vec::new(),
        test_layout: TestLayout::Mirrored,
        rule_packs: vec!["sveltekit".to_owned()],
        select: vec!["FPSK".to_owned()],
    })
}

fn ignored_python_directory(name: Option<&str>) -> bool {
    matches!(
        name,
        Some(
            ".git"
                | ".venv"
                | "venv"
                | "node_modules"
                | ".svelte-kit"
                | "target"
                | "dist"
                | "build"
                | "__pycache__"
        )
    )
}

fn ignored_web_directory(name: Option<&str>) -> bool {
    ignored_python_directory(name)
        || matches!(
            name,
            Some(
                ".svelte-kit"
                    | "coverage"
                    | "fixture"
                    | "fixtures"
                    | "example"
                    | "examples"
                    | "template"
                    | "templates"
                    | "demo"
                    | "demos"
            )
        )
}

fn is_svelte_config(path: &Path) -> bool {
    let Some(name) = path.file_name().and_then(|value| value.to_str()) else {
        return false;
    };
    matches!(
        name,
        "svelte.config.js" | "svelte.config.cjs" | "svelte.config.mjs" | "svelte.config.ts"
    )
}

fn valid_sveltekit_root(repository: &Path, root: &Path) -> bool {
    if !regular_directory(&root.join("src"))
        || !(regular_file(&root.join("tsconfig.json")) || regular_file(&root.join("jsconfig.json")))
    {
        return false;
    }
    let Ok(relative) = root
        .join("package.json")
        .strip_prefix(repository)
        .map(Path::to_path_buf)
    else {
        return false;
    };
    let Ok(directory) = open_repository(repository) else {
        return false;
    };
    let Ok(Some(snapshot)) = read_optional(&directory, &relative) else {
        return false;
    };
    let Ok(package) = serde_json::from_slice::<serde_json::Value>(&snapshot.content) else {
        return false;
    };
    ["dependencies", "devDependencies"]
        .iter()
        .filter_map(|key| package.get(key).and_then(serde_json::Value::as_object))
        .filter_map(|dependencies| dependencies.get("@sveltejs/kit"))
        .filter_map(serde_json::Value::as_str)
        .any(|version| !version.trim().is_empty())
}

fn regular_file(path: &Path) -> bool {
    match fs::symlink_metadata(path) {
        Ok(metadata) => metadata.is_file(),
        Err(_) => false,
    }
}

fn regular_directory(path: &Path) -> bool {
    match fs::symlink_metadata(path) {
        Ok(metadata) => metadata.is_dir(),
        Err(_) => false,
    }
}

fn target_name(root: &str) -> String {
    if root == DEFAULT_TARGET_ROOT {
        return WEB_TARGET_NAME.to_owned();
    }
    root.rsplit('/')
        .next()
        .unwrap_or("web")
        .chars()
        .map(|character| {
            if character.is_ascii_alphanumeric() || character == '-' || character == '_' {
                character.to_ascii_lowercase()
            } else {
                '-'
            }
        })
        .collect::<String>()
        .trim_matches('-')
        .to_owned()
}

fn assign_target_names(targets: &mut [DetectedTarget], reserve_python: bool) {
    let mut used: BTreeSet<String> = BTreeSet::new();
    if reserve_python {
        used.insert(PYTHON_TARGET_NAME.to_owned());
    }
    for target in targets {
        let base = if target.name.is_empty() {
            "web".to_owned()
        } else {
            target.name.clone()
        };
        let mut name = base.clone();
        let mut suffix = 2;
        while !used.insert(name.clone()) {
            name = format!("{base}-{suffix}");
            suffix += 1;
        }
        target.name = name;
    }
}

pub(crate) fn local_config(repository: &Path) -> Result<Option<PathBuf>, String> {
    let directory = open_repository(repository)?;
    let fensu = repository.join("fensu.toml");
    if read_optional(&directory, Path::new("fensu.toml"))?.is_some() {
        return Ok(Some(fensu));
    }
    let pyproject = repository.join("pyproject.toml");
    let Some(snapshot) = read_optional(&directory, Path::new("pyproject.toml"))? else {
        return Ok(None);
    };
    let configured = match toml::from_slice::<toml::Value>(&snapshot.content) {
        Ok(document) => document
            .get("tool")
            .and_then(|tool| tool.get("fensu"))
            .is_some(),
        Err(_) => String::from_utf8_lossy(&snapshot.content).contains("[tool.fensu"),
    };
    Ok(configured.then_some(pyproject))
}

pub(crate) fn existing_configuration(
    path: &Path,
    options: &InitOptions,
) -> Result<CliOutput, String> {
    let parent = path
        .parent()
        .ok_or_else(|| "Configuration has no parent directory.".to_owned())?;
    let name = path
        .file_name()
        .ok_or_else(|| "Configuration has no file name.".to_owned())?;
    let directory = open_repository(parent)?;
    let snapshot = read_optional(&directory, Path::new(name))?
        .ok_or_else(|| format!("Configuration disappeared: {}", path.display()))?;
    let text = String::from_utf8(snapshot.content)
        .map_err(|error| format!("Configuration is not UTF-8: {error}"))?;
    let pyproject = path.file_name().and_then(|name| name.to_str()) == Some(CONFIG_PYPROJECT_FILE);
    if let Err(error) = validate_document(&text, pyproject) {
        return Err(format!(
            "Fensu configuration already exists but is not usable: {}\n{error}\nEdit that file, \
             or delete it and rerun fensu init.",
            path.display()
        ));
    }
    if requests_scopes(options) {
        let action = if pyproject {
            "Edit [tool.fensu] in pyproject.toml manually; fensu target add supports fensu.toml only"
        } else {
            "Edit that file, use fensu target add for a safe explicit addition"
        };
        return Err(format!(
            "Fensu configuration already exists: {}\nRefusing to overwrite it, so explicit init \
             options were not applied. {action}, or delete it and rerun fensu init.",
            path.display(),
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
        .filter_entry(|entry| !ignored_python_directory(entry.file_name().to_str()))
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
            .is_some_and(|candidate| regular_file(&candidate.join("__init__.py")));
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
