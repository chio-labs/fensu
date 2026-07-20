use std::collections::{BTreeMap, BTreeSet};
use std::fs;
use std::path::{Path, PathBuf};

use fensu_facts::snapshot::main::walk_python_files::walk_python_files;
use sha2::{Digest, Sha256};

use crate::configuration::main::load_optional;
use crate::mapping::constants::INIT_MODULE;
use crate::mapping::models::{MappingProject, MappingSource, SourceSnapshot};

const EXCLUDED: &[&str] = &[
    ".git",
    ".mypy_cache",
    ".nox",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "venv",
];

pub(crate) fn resolve(explicit_roots: &[String]) -> Result<MappingProject, String> {
    let cwd = dunce::canonicalize(std::env::current_dir().map_err(|error| error.to_string())?)
        .map_err(|error| error.to_string())?;
    if !explicit_roots.is_empty() {
        let repo_root = find_project_root(&cwd);
        let cache_enabled = load_optional::load_optional(&cwd)
            .ok()
            .flatten()
            .is_none_or(|(_, config)| config.cache_enabled);
        let mut sources = Vec::new();
        for value in explicit_roots {
            let candidate = Path::new(value);
            let joined = if candidate.is_absolute() {
                candidate.to_path_buf()
            } else {
                cwd.join(candidate)
            };
            let scan_path = dunce::canonicalize(&joined)
                .map_err(|_| format!("Mapping root path does not exist: {value}"))?;
            if !scan_path.is_dir() {
                return Err(format!("Mapping root path does not exist: {value}"));
            }
            sources.push(MappingSource {
                import_root: scan_path.clone(),
                scan_path,
            });
        }
        return Ok(MappingProject {
            repo_root,
            sources,
            cache_enabled,
        });
    }
    if let Some((path, loaded)) = load_optional::load_optional(&cwd)? {
        let repo_root = dunce::canonicalize(path.parent().unwrap_or(Path::new(".")))
            .map_err(|error| error.to_string())?;
        let sources = configured_sources(&repo_root, &loaded)?;
        return Ok(MappingProject {
            repo_root,
            sources,
            cache_enabled: loaded.cache_enabled,
        });
    }
    let repo_root = find_project_root(&cwd);
    let source_root = if repo_root.join("src").is_dir() {
        repo_root.join("src")
    } else {
        repo_root.clone()
    };
    if !contains_python(&source_root) {
        return Err(format!(
            "No Python files found under inferred root: {}",
            source_root.display()
        ));
    }
    Ok(MappingProject {
        repo_root,
        sources: vec![MappingSource {
            scan_path: source_root.clone(),
            import_root: source_root,
        }],
        cache_enabled: true,
    })
}

fn configured_sources(
    repo_root: &Path,
    loaded: &crate::models::Config,
) -> Result<Vec<MappingSource>, String> {
    let runtime = resolve_configured_paths(repo_root, &loaded.roots)?;
    let tests = resolve_configured_paths(repo_root, &loaded.tests)?;
    let tooling = resolve_configured_paths(repo_root, &loaded.tooling)?;
    let mut missing = loaded
        .roots
        .iter()
        .zip(&runtime)
        .filter(|(_, path)| !path.is_dir())
        .map(|(value, _)| value.clone())
        .collect::<Vec<_>>();
    if !missing.is_empty() {
        missing.sort();
        return Err(format!(
            "Configured root path(s) do not exist: {}.",
            missing.join(", ")
        ));
    }
    validate_cross_scope_paths(&runtime, &tests, &tooling)?;
    validate_import_package_names(&runtime, &tests, &tooling)?;
    Ok(runtime
        .into_iter()
        .map(|scan_path| MappingSource {
            import_root: scan_path
                .parent()
                .map(Path::to_path_buf)
                .unwrap_or_else(|| scan_path.clone()),
            scan_path,
        })
        .collect())
}

fn resolve_configured_paths(repo_root: &Path, values: &[String]) -> Result<Vec<PathBuf>, String> {
    values
        .iter()
        .map(|value| {
            let configured = Path::new(value);
            let joined = if configured.is_absolute() {
                configured.to_path_buf()
            } else {
                repo_root.join(configured)
            };
            let resolved = dunce::canonicalize(&joined).unwrap_or_else(|_| normalize_path(&joined));
            if resolved.strip_prefix(repo_root).is_err() {
                return Err(format!(
                    "Configured path must resolve inside the repository: {value}"
                ));
            }
            Ok(resolved)
        })
        .collect()
}

fn validate_cross_scope_paths(
    runtime: &[PathBuf],
    tests: &[PathBuf],
    tooling: &[PathBuf],
) -> Result<(), String> {
    for (owner, paths, other_owner, other_paths) in [
        ("roots", runtime, "tests", tests),
        ("roots", runtime, "tooling", tooling),
        ("tests", tests, "tooling", tooling),
    ] {
        let paths = paths.iter().collect::<BTreeSet<_>>();
        let others = other_paths.iter().collect::<BTreeSet<_>>();
        if let Some(duplicate) = paths.intersection(&others).next() {
            return Err(format!(
                "Configured path cannot belong to both {owner} and {other_owner}: {}",
                duplicate.display()
            ));
        }
    }
    Ok(())
}

fn validate_import_package_names(
    runtime: &[PathBuf],
    tests: &[PathBuf],
    tooling: &[PathBuf],
) -> Result<(), String> {
    for (owner, paths, other_owner, other_paths) in [
        ("Runtime", runtime, "test", tests),
        ("Runtime", runtime, "tooling", tooling),
        ("test", tests, "tooling", tooling),
    ] {
        let names = package_names(paths);
        let others = package_names(other_paths);
        let duplicates = names.intersection(&others).cloned().collect::<Vec<_>>();
        if !duplicates.is_empty() {
            return Err(format!(
                "{owner} and {other_owner} roots must not claim the same import package: {}",
                duplicates.join(", ")
            ));
        }
    }
    Ok(())
}

fn package_names(paths: &[PathBuf]) -> BTreeSet<String> {
    paths
        .iter()
        .filter_map(|path| path.file_name())
        .map(|name| name.to_string_lossy().into_owned())
        .collect()
}

fn normalize_path(path: &Path) -> PathBuf {
    let mut normalized = PathBuf::new();
    for component in path.components() {
        match component {
            std::path::Component::ParentDir => {
                normalized.pop();
            }
            std::path::Component::CurDir => {}
            _ => normalized.push(component.as_os_str()),
        }
    }
    normalized
}

pub(crate) fn discover(
    sources: &[MappingSource],
    repo_root: &Path,
) -> Result<Vec<SourceSnapshot>, String> {
    let roots = sources
        .iter()
        .map(|source| source.scan_path.clone())
        .collect::<Vec<_>>();
    let mut discovered = BTreeMap::<PathBuf, PathBuf>::new();
    for (source, entries) in sources.iter().zip(walk_python_files(&roots)) {
        for entry in entries {
            let (Some(path), Some(parts)) = (entry.canonical_path, entry.root_relative_parts)
            else {
                continue;
            };
            if parts
                .iter()
                .any(|part| EXCLUDED.contains(&part.to_string_lossy().as_ref()))
            {
                continue;
            }
            discovered
                .entry(path)
                .or_insert_with(|| source.import_root.clone());
        }
    }
    let mut snapshots = Vec::new();
    for (path, import_root) in discovered {
        let source = fs::read(&path)
            .map_err(|error| format!("Could not read {}: {error}", path.display()))?;
        let relative_path = safe_path(&path, repo_root);
        let import_root_identity = safe_path(&import_root, repo_root);
        let module_name = module_name(&path, &import_root)?;
        let source_fingerprint = format!("{:x}", Sha256::digest(&source));
        snapshots.push(SourceSnapshot {
            path,
            relative_path,
            import_root_identity,
            module_name,
            source,
            source_fingerprint,
        });
    }
    Ok(snapshots)
}

fn find_project_root(cwd: &Path) -> PathBuf {
    cwd.ancestors()
        .find(|directory| {
            directory.join(".git").exists() || directory.join("pyproject.toml").is_file()
        })
        .unwrap_or(cwd)
        .to_path_buf()
}

fn contains_python(root: &Path) -> bool {
    walk_python_files(&[root.to_path_buf()])
        .first()
        .is_some_and(|entries| !entries.is_empty())
}

fn safe_path(path: &Path, repo_root: &Path) -> String {
    path.strip_prefix(repo_root)
        .unwrap_or(path)
        .to_string_lossy()
        .replace('\\', "/")
}

fn module_name(path: &Path, import_root: &Path) -> Result<String, String> {
    let relative = path.strip_prefix(import_root).map_err(|error| {
        format!(
            "Could not derive module name for {}: {error}",
            path.display()
        )
    })?;
    let mut parts = relative
        .components()
        .map(|part| part.as_os_str().to_string_lossy().into_owned())
        .collect::<Vec<_>>();
    if let Some(last) = parts.last_mut() {
        *last = last.trim_end_matches(".py").to_owned();
    }
    if parts.last().is_some_and(|part| part == INIT_MODULE) {
        parts.pop();
    }
    Ok(parts.join("."))
}
