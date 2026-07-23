use std::collections::{BTreeMap, HashMap, HashSet};
use std::fs;
use std::path::Path;

use fensu_facts::extension::models::ProgramHandle;
use ruff_python_ast::PythonVersion;
use sha2::{Digest, Sha256};
use walkdir::WalkDir;

use crate::constants::{
    GLOB_ALL, PYTHON_CACHE_DIRECTORY, ROLE_HELPERS, ROLE_MAIN, ROLE_RULES, SCOPE_TOOLING,
    SUFFIX_INIT,
};
use crate::models::{Config, Fault, ScopedSource, ThresholdUse};

pub(crate) fn resolved_thresholds(
    source: &ScopedSource,
    config: &Config,
    codes: &[String],
) -> (HashMap<String, u32>, Vec<ThresholdUse>) {
    let mut values = config.thresholds.clone();
    if let Some(role) = role(source).and_then(|role| config.role_thresholds.get(&role)) {
        values.extend(role.clone());
    }
    let required = required_thresholds(codes);
    let mut uses = Vec::new();
    for (order, override_) in config.threshold_overrides.iter().enumerate() {
        let Some(pattern) = override_
            .paths
            .iter()
            .filter(|pattern| path_matches(&source.repository_path, pattern))
            .max_by_key(|pattern| pattern.len())
        else {
            continue;
        };
        for (name, value) in &override_.thresholds {
            if required.contains(name.as_str()) {
                values.insert(name.clone(), *value);
                uses.push(ThresholdUse {
                    repository_path: source.repository_path.clone(),
                    threshold: name.clone(),
                    override_order: order,
                    matched_pattern: pattern.clone(),
                    reason: override_.reason.clone(),
                    effective_value: *value,
                });
            }
        }
    }
    (values, uses)
}

pub(crate) fn required_thresholds(codes: &[String]) -> HashSet<&'static str> {
    let mut names = HashSet::new();
    for code in codes {
        match code.as_str() {
            "FFR301" => names.extend(["max_helpers_container_modules", "max_role_depth"]),
            "FFR302" => names.extend(["max_main_container_modules", "max_role_depth"]),
            "FFR308" => {
                names.insert("min_shared_domain_prefix_packages");
            }
            "FFR601" => {
                names.insert("max_file_lines");
            }
            "FFR703" => {
                names.insert("max_script_entrypoint_lines");
            }
            "FFS001" => {
                names.insert("max_statements");
            }
            "FFS002" => {
                names.insert("max_distinct_calls");
            }
            "FFS003" => {
                names.insert("max_locals");
            }
            "FFS010" => {
                names.insert("max_arguments");
            }
            "FFS011" => {
                names.insert("max_statements_global");
            }
            "FFS120" => {
                names.insert("max_positional_args");
            }
            "FFR707" => {
                names.insert("min_custom_rule_test_cases");
            }
            _ => {}
        }
    }
    names
}

pub(crate) fn apply_exceptions(
    faults: Vec<Fault>,
    config: &Config,
) -> Result<(Vec<Fault>, usize), String> {
    let mut applied = HashSet::new();
    let retained = faults
        .into_iter()
        .filter(|fault| {
            let relative = config.exceptions.iter().find(|entry| {
                entry.rule == fault.code
                    && fault.path.replace('\\', "/").ends_with(&entry.path)
                    && entry.symbols.is_empty()
            });
            if let Some(entry) = relative {
                applied.insert((entry.rule.clone(), entry.path.clone()));
                false
            } else {
                true
            }
        })
        .collect::<Vec<_>>();
    if let Some(stale) = config.exceptions.iter().find(|entry| {
        entry.symbols.is_empty() && !applied.contains(&(entry.rule.clone(), entry.path.clone()))
    }) {
        return Err(format!(
            "Rule exception no longer matches a fault: {} {}. Remove it or update its scope. Reason: {}",
            stale.rule, stale.path, stale.reason
        ));
    }
    Ok((retained, applied.len()))
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

pub(crate) fn validate_package_names(root: &Path, config: &Config) -> Result<(), String> {
    let runtime = config
        .roots
        .iter()
        .filter_map(|path| root.join(path).file_name().map(|name| name.to_owned()))
        .collect::<HashSet<_>>();
    let tooling = config
        .tooling
        .iter()
        .filter_map(|path| root.join(path).file_name().map(|name| name.to_owned()))
        .collect::<HashSet<_>>();
    if let Some(name) = runtime.intersection(&tooling).next() {
        return Err(format!(
            "Runtime and tooling roots must not claim the same import package: {}.",
            name.to_string_lossy()
        ));
    }
    Ok(())
}

pub(crate) fn path_matches(path: &str, pattern: &str) -> bool {
    let value = if pattern.contains('/') || pattern == GLOB_ALL {
        pattern.as_bytes().to_vec()
    } else {
        format!("**/{pattern}").into_bytes()
    };
    wildcard_matches(path.as_bytes(), &value, 0, 0, &mut HashMap::new())
}

fn wildcard_matches(
    path: &[u8],
    pattern: &[u8],
    path_index: usize,
    pattern_index: usize,
    memo: &mut HashMap<(usize, usize), bool>,
) -> bool {
    if let Some(result) = memo.get(&(path_index, pattern_index)) {
        return *result;
    }
    let result = if pattern_index == pattern.len() {
        path_index == path.len()
    } else if pattern[pattern_index..].starts_with(b"**/") {
        wildcard_matches(path, pattern, path_index, pattern_index + 3, memo)
            || (path_index..path.len()).any(|index| {
                path[index] == b'/'
                    && wildcard_matches(path, pattern, index + 1, pattern_index + 3, memo)
            })
    } else if pattern[pattern_index..].starts_with(b"**") {
        (path_index..=path.len())
            .any(|index| wildcard_matches(path, pattern, index, pattern_index + 2, memo))
    } else if pattern[pattern_index] == b'*' {
        (path_index..=path.len())
            .take_while(|index| {
                *index == path.len() || path.get(*index).is_some_and(|value| *value != b'/')
            })
            .any(|index| wildcard_matches(path, pattern, index, pattern_index + 1, memo))
    } else {
        path.get(path_index) == pattern.get(pattern_index)
            && wildcard_matches(path, pattern, path_index + 1, pattern_index + 1, memo)
    };
    memo.insert((path_index, pattern_index), result);
    result
}

pub(crate) fn check_identity(
    root: &Path,
    config: &Config,
    sources: &[ScopedSource],
    warnings: bool,
) -> String {
    let mut digest = Sha256::new();
    digest.update(b"fensu-native-check-v3\0");
    digest.update(env!("CARGO_PKG_VERSION").as_bytes());
    digest.update(&config.raw);
    digest.update([u8::from(warnings)]);
    for source in sources {
        digest.update(source.repository_path.as_bytes());
        digest.update(source.fingerprint.as_bytes());
    }
    digest_project_observations(&mut digest, root, config);
    format!("{:x}", digest.finalize())
}

fn digest_project_observations(digest: &mut Sha256, root: &Path, config: &Config) {
    let mut entries = BTreeMap::new();
    for configured_root in config
        .roots
        .iter()
        .chain(&config.tests)
        .chain(&config.tooling)
    {
        for entry in WalkDir::new(root.join(configured_root))
            .follow_links(false)
            .into_iter()
            .filter_map(Result::ok)
            .skip(1)
        {
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
            match fs::read(&filesystem_path) {
                Ok(content) => digest.update(Sha256::digest(content)),
                Err(error) => digest.update(error.to_string().as_bytes()),
            }
        }
    }
    let pyproject = root.join("pyproject.toml");
    if let Ok(content) = fs::read(pyproject) {
        digest.update(b"pyproject.toml\0");
        digest.update(Sha256::digest(content));
    }
}

pub(crate) fn hex_digest(bytes: &[u8]) -> String {
    let digest = Sha256::digest(bytes);
    format!("{digest:x}")
}

pub(crate) fn apply_rule_ignores(faults: Vec<Fault>, root: &Path, config: &Config) -> Vec<Fault> {
    faults
        .into_iter()
        .filter(|fault| {
            let Some(repository_path) = Path::new(&fault.path)
                .strip_prefix(root)
                .ok()
                .map(|path| path.to_string_lossy().replace('\\', "/"))
            else {
                return true;
            };
            !config.rule_ignores.iter().any(|entry| {
                entry
                    .rules
                    .iter()
                    .any(|selector| fault.code.starts_with(selector))
                    && entry
                        .paths
                        .iter()
                        .any(|pattern| path_matches(&repository_path, pattern))
            })
        })
        .collect()
}

pub(crate) fn bool_text(value: bool) -> String {
    if value { "true" } else { "false" }.to_owned()
}

pub(crate) fn relative(path: &Path, root: &Path) -> Option<String> {
    path.strip_prefix(root)
        .ok()
        .map(|path| path.to_string_lossy().replace('\\', "/"))
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
        .unwrap_or_else(|| std::process::abort())
}
