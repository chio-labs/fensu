use std::collections::{BTreeMap, HashMap, HashSet};
use std::fs;
use std::path::{Component, Path, PathBuf};

use fensu_facts::extension::models::ProgramHandle;
use ruff_python_ast::PythonVersion;
use sha2::{Digest, Sha256};
use walkdir::WalkDir;

use crate::check::_helpers::project as web;
use crate::check::models::CheckIdentityRequest;
use crate::constants::{
    GLOB_ALL, PYTHON_CACHE_DIRECTORY, ROLE_HELPERS, ROLE_MAIN, ROLE_RULES, SCOPE_TOOLING,
    SUFFIX_INIT,
};
use crate::models::{Config, Fault, ScopedSource};

struct WildcardMatcher<'a> {
    path: &'a [u8],
    pattern: &'a [u8],
    memo: HashMap<(usize, usize), bool>,
}

impl WildcardMatcher<'_> {
    fn matches(&mut self, path_index: usize, pattern_index: usize) -> bool {
        if let Some(result) = self.memo.get(&(path_index, pattern_index)) {
            return *result;
        }
        let result = if pattern_index == self.pattern.len() {
            path_index == self.path.len()
        } else if self.pattern[pattern_index..].starts_with(b"**/") {
            self.matches(path_index, pattern_index + 3)
                || (path_index..self.path.len()).any(|index| {
                    self.path[index] == b'/' && self.matches(index + 1, pattern_index + 3)
                })
        } else if self.pattern[pattern_index..].starts_with(b"**") {
            (path_index..=self.path.len()).any(|index| self.matches(index, pattern_index + 2))
        } else if self.pattern[pattern_index] == b'*' {
            let mut index = path_index;
            let mut matched = false;
            while index <= self.path.len() {
                matched |= self.matches(index, pattern_index + 1);
                if matched || index == self.path.len() || self.path[index] == b'/' {
                    break;
                }
                index += 1;
            }
            matched
        } else {
            self.path.get(path_index) == self.pattern.get(pattern_index)
                && self.matches(path_index + 1, pattern_index + 1)
        };
        self.memo.insert((path_index, pattern_index), result);
        result
    }
}

pub(crate) fn role(source: &ScopedSource) -> Option<String> {
    let file = source.relative_parts.last()?;
    if let Some(value) = file.strip_suffix(".py") {
        if matches!(value, "models" | "types" | "constants" | "exceptions") {
            return Some(value.to_owned());
        }
    }
    for part in &source.relative_parts[..source.relative_parts.len().saturating_sub(1)] {
        if source.scope == SCOPE_TOOLING && part == ROLE_RULES {
            return Some(part.clone());
        }
        if matches!(part.as_str(), ROLE_MAIN | ROLE_HELPERS | "classes") {
            return Some(if part == ROLE_HELPERS {
                "helpers".to_owned()
            } else {
                part.clone()
            });
        }
    }
    None
}

pub(crate) fn is_main_module(source: &ScopedSource) -> bool {
    source
        .relative_parts
        .iter()
        .take(source.relative_parts.len().saturating_sub(1))
        .find(|part| {
            matches!(
                part.as_str(),
                "main" | "_helpers" | "classes" | "models" | "types" | "constants" | "exceptions"
            )
        })
        .is_some_and(|part| part == ROLE_MAIN)
}

pub(crate) fn is_entry_module(source: &ScopedSource) -> bool {
    is_main_module(source)
        && source
            .relative_parts
            .last()
            .is_some_and(|part| part != SUFFIX_INIT)
}

pub(crate) fn scope_roots(config: &Config) -> Vec<(String, String)> {
    config
        .roots
        .iter()
        .map(|path| ("root".to_owned(), path.clone()))
        .chain(
            config
                .tests
                .iter()
                .map(|path| ("test".to_owned(), path.clone())),
        )
        .chain(
            config
                .tooling
                .iter()
                .map(|path| ("tooling".to_owned(), path.clone())),
        )
        .collect()
}

pub(crate) fn source_module_name(source: &ScopedSource, root: &Path) -> String {
    source
        .path
        .strip_prefix(source.root.parent().unwrap_or(root))
        .unwrap_or(&source.path)
        .to_string_lossy()
        .trim_end_matches(".py")
        .trim_end_matches("/__init__")
        .replace(['/', '\\'], ".")
}

pub(crate) fn validate_scope_roots(root: &Path, config: &Config) -> Result<(), String> {
    let scopes = [
        ("roots", "Runtime", &config.roots),
        ("tests", "test", &config.tests),
        ("tooling", "tooling", &config.tooling),
    ];
    let mut resolved: Vec<(&str, &str, Vec<PathBuf>)> = Vec::new();
    for (owner, label, configured) in scopes {
        let mut paths: Vec<PathBuf> = Vec::new();
        for value in configured {
            paths.push(resolve_scope_path(root, value)?);
        }
        resolved.push((owner, label, paths));
    }
    let missing = config
        .roots
        .iter()
        .zip(&resolved[0].2)
        .filter(|(_, path)| !path.is_dir())
        .map(|(configured, _)| configured.as_str())
        .collect::<Vec<_>>();
    if !missing.is_empty() {
        return Err(format!(
            "Configured root path(s) do not exist: {}.",
            missing.join(", ")
        ));
    }
    for index in 0..resolved.len() {
        let (owner, label, paths) = &resolved[index];
        for (other_owner, other_label, other_paths) in &resolved[index + 1..] {
            if let Some(path) = paths.iter().filter(|path| other_paths.contains(path)).min() {
                return Err(format!(
                    "Configured path cannot belong to both {owner} and {other_owner}: {}",
                    path.display()
                ));
            }
            let packages = paths
                .iter()
                .filter_map(|path| path.file_name())
                .collect::<HashSet<_>>();
            let other_packages = other_paths
                .iter()
                .filter_map(|path| path.file_name())
                .collect::<HashSet<_>>();
            if let Some(name) = packages.intersection(&other_packages).min() {
                return Err(format!(
                    "{label} and {other_label} roots must not claim the same import package: {}",
                    name.to_string_lossy()
                ));
            }
        }
    }
    Ok(())
}

fn resolve_scope_path(root: &Path, value: &str) -> Result<PathBuf, String> {
    let configured = Path::new(value);
    let candidate = if configured.is_absolute() {
        configured.to_path_buf()
    } else {
        root.join(configured)
    };
    let normalized = normalize_path(&candidate);
    let resolved = if normalized.exists() {
        normalized
            .canonicalize()
            .map_err(|error| format!("Could not resolve configured path {value}: {error}"))?
    } else {
        normalized
    };
    if !resolved.starts_with(root) {
        return Err(format!(
            "Configured path must resolve inside the repository: {value}"
        ));
    }
    Ok(resolved)
}

fn normalize_path(path: &Path) -> PathBuf {
    let mut normalized = PathBuf::new();
    for component in path.components() {
        match component {
            Component::CurDir => {}
            Component::ParentDir => {
                let _ = normalized.pop();
            }
            other => normalized.push(other.as_os_str()),
        }
    }
    normalized
}

pub(crate) fn path_matches(path: &str, pattern: &str) -> bool {
    let value = if pattern.contains('/') || pattern == GLOB_ALL {
        pattern.as_bytes().to_vec()
    } else {
        format!("**/{pattern}").into_bytes()
    };
    WildcardMatcher {
        path: path.as_bytes(),
        pattern: &value,
        memo: HashMap::new(),
    }
    .matches(0, 0)
}

pub(crate) fn check_identity(request: CheckIdentityRequest<'_>) -> Result<String, String> {
    let CheckIdentityRequest {
        root,
        project_root,
        config,
        sources,
        project_inputs,
        warnings,
    } = request;
    let mut digest = Sha256::new();
    digest.update(b"fensu-native-check-v4\0");
    digest.update(env!("CARGO_PKG_VERSION").as_bytes());
    digest.update(&config.raw);
    digest_text(&mut digest, &config.analyzer.to_string());
    digest_text(&mut digest, config.analyzer.cache_contract());
    digest_text(&mut digest, config.analyzer.parser_contract());
    digest_text(&mut digest, config.target.as_deref().unwrap_or_default());
    digest_text(&mut digest, &config.target_root);
    digest.update([u8::from(warnings)]);
    for source in sources {
        digest_text(&mut digest, &source.analyzer.to_string());
        digest_text(&mut digest, &source.target_identity);
        digest_text(&mut digest, source.parser_contract);
        digest_text(&mut digest, &source.repository_path);
        digest_text(&mut digest, &source.fingerprint);
    }
    for input in project_inputs {
        digest_text(&mut digest, &input.repository_path);
        digest_text(&mut digest, &input.target_path);
        digest_text(&mut digest, &input.fingerprint);
    }
    digest_project_observations(&mut digest, root, project_root, config)?;
    Ok(format!("{:x}", digest.finalize()))
}

fn digest_text(digest: &mut Sha256, value: &str) {
    digest.update(value.len().to_be_bytes());
    digest.update(value.as_bytes());
}

fn digest_project_observations(
    digest: &mut Sha256,
    root: &Path,
    project_root: &Path,
    config: &Config,
) -> Result<(), String> {
    let mut entries: BTreeMap<String, (u8, PathBuf)> = BTreeMap::new();
    for configured_root in config
        .roots
        .iter()
        .chain(&config.tests)
        .chain(&config.tooling)
    {
        let scan_root = project_root.join(configured_root);
        if !scan_root.exists() {
            continue;
        }
        for result in WalkDir::new(scan_root)
            .follow_links(false)
            .into_iter()
            .filter_entry(|entry| {
                config.analyzer == crate::analyzer::AnalyzerId::Python
                    || web::is_artifact_entry(entry)
            })
            .skip(1)
        {
            let entry = result.map_err(|error| {
                format!(
                    "Could not fingerprint project observations under {configured_root}: {error}"
                )
            })?;
            if entry.file_type().is_dir() && entry.file_name() == PYTHON_CACHE_DIRECTORY {
                continue;
            }
            if entry.file_type().is_file()
                && matches!(
                    entry.path().extension().and_then(|value| value.to_str()),
                    Some("pyc" | "pyo")
                )
            {
                continue;
            }
            let Ok(path) = entry.path().strip_prefix(root) else {
                continue;
            };
            let repository_path = path.to_string_lossy().replace('\\', "/");
            let kind = if entry.file_type().is_dir() {
                b'd'
            } else if entry.file_type().is_file() {
                b'f'
            } else if entry.file_type().is_symlink() {
                b'l'
            } else {
                b'o'
            };
            entries.insert(repository_path, (kind, entry.path().to_path_buf()));
        }
    }
    for (path, (kind, filesystem_path)) in entries {
        digest.update(path.as_bytes());
        digest.update([kind]);
        if filesystem_path.extension().and_then(|value| value.to_str()) == Some("pyi") {
            let content = fs::read(&filesystem_path).map_err(|error| {
                format!(
                    "Could not fingerprint Python support file {}: {error}",
                    filesystem_path.display()
                )
            })?;
            digest.update(Sha256::digest(content));
        }
    }
    let pyproject = project_root.join("pyproject.toml");
    if pyproject.exists() {
        let content = fs::read(&pyproject).map_err(|error| {
            format!(
                "Could not fingerprint project input {}: {error}",
                pyproject.display()
            )
        })?;
        digest.update(b"pyproject.toml\0");
        digest.update(Sha256::digest(content));
    }
    Ok(())
}

pub(crate) fn hex_digest(bytes: &[u8]) -> String {
    let digest = Sha256::digest(bytes);
    format!("{digest:x}")
}

pub(crate) fn apply_rule_ignores(faults: Vec<Fault>, root: &Path, config: &Config) -> Vec<Fault> {
    let mut retained: Vec<Fault> = Vec::new();
    for fault in faults {
        let Ok(path) = Path::new(&fault.path).strip_prefix(root) else {
            retained.push(fault);
            continue;
        };
        let repository_path = path.to_string_lossy().replace('\\', "/");
        let mut ignored = false;
        for entry in &config.rule_ignores {
            let rule_matches = entry
                .rules
                .iter()
                .any(|selector| fault.code.starts_with(selector));
            let path_matches_entry = entry
                .paths
                .iter()
                .any(|pattern| path_matches(&repository_path, pattern));
            if rule_matches && path_matches_entry {
                ignored = true;
                break;
            }
        }
        if !ignored {
            retained.push(fault);
        }
    }
    retained
}

pub(crate) fn bool_text(value: bool) -> String {
    if value { "true" } else { "false" }.to_owned()
}

pub(crate) fn relative(path: &Path, root: &Path) -> Option<String> {
    let Ok(relative) = path.strip_prefix(root) else {
        return None;
    };
    Some(relative.to_string_lossy().replace('\\', "/"))
}

pub(crate) fn python_version() -> PythonVersion {
    PythonVersion {
        major: 3,
        minor: 12,
    }
}

pub(crate) fn program(source: &ScopedSource) -> &ProgramHandle {
    source
        .program
        .as_ref()
        .and_then(crate::models::ParsedProgram::as_python)
        .unwrap_or_else(|| std::process::abort())
}
