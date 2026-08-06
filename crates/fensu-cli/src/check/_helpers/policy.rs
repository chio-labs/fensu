use std::collections::{BTreeMap, HashMap, HashSet};
use std::ffi::OsString;
use std::fs;
use std::path::{Path, PathBuf};

use fensu_facts::extension::models::ProgramHandle;
use ruff_python_ast::PythonVersion;
use sha2::{Digest, Sha256};
use walkdir::WalkDir;

use crate::catalogue::main::rule_metadata::rule_metadata;
use crate::constants::{
    GLOB_ALL, PYTHON_CACHE_DIRECTORY, ROLE_HELPERS, ROLE_MAIN, ROLE_RULES, SCOPE_TOOLING,
    SUFFIX_INIT,
};
use crate::models::{Config, Fault, ScopedSource, ThresholdUse};

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
    let mut uses: Vec<ThresholdUse> = Vec::new();
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
    let mut names: HashSet<&'static str> = HashSet::new();
    for code in codes {
        if let Some(metadata) = rule_metadata(code) {
            names.extend(metadata.thresholds.iter().map(String::as_str));
        }
    }
    names
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
    let mut runtime: HashSet<OsString> = HashSet::new();
    for path in &config.roots {
        if let Some(name) = root.join(path).file_name() {
            runtime.insert(name.to_owned());
        }
    }
    let mut tooling: HashSet<OsString> = HashSet::new();
    for path in &config.tooling {
        if let Some(name) = root.join(path).file_name() {
            tooling.insert(name.to_owned());
        }
    }
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
    WildcardMatcher {
        path: path.as_bytes(),
        pattern: &value,
        memo: HashMap::new(),
    }
    .matches(0, 0)
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
    let mut entries: BTreeMap<String, (u8, PathBuf)> = BTreeMap::new();
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
        .unwrap_or_else(|| std::process::abort())
}
