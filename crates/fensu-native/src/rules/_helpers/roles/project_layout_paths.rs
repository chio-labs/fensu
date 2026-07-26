//! Filesystem and ownership helpers shared by native project layout rules.

use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};

use unicode_ident::{is_xid_continue, is_xid_start};

use crate::rules::models::NativeRuleContext;

pub(crate) const HELPERS: &str = "_helpers";
pub(crate) const INIT_FILE: &str = "__init__.py";
pub(crate) const PYTHON_CACHE: &str = "__pycache__";
pub(crate) const ROOT_SCOPE: &str = "root";
const LEGACY_HELPERS: &str = "helpers";
const MAIN_ROLE: &str = "main";
const MINIMUM_DOMAIN_PARTS: usize = 2;
const MINIMUM_SUBDOMAIN_PARTS: usize = 3;
const PYTHON_EXTENSION: &str = "py";
pub(crate) const ROLE_NAMES: &[&str] = &[
    MAIN_ROLE,
    HELPERS,
    "classes",
    "models",
    "types",
    "constants",
    "exceptions",
];
const ROLE_FILES: &[&str] = &[
    "main.py",
    "helpers.py",
    "classes.py",
    "models.py",
    "types.py",
    "constants.py",
    "exceptions.py",
];

pub(crate) fn role_package(context: &NativeRuleContext, role: &str) -> Option<PathBuf> {
    let index = context.relative_parts[..context.relative_parts.len().saturating_sub(1)]
        .iter()
        .position(|part| ROLE_NAMES.contains(&part.as_str()))?;
    (context.relative_parts[index] == role).then(|| {
        scope_root(context).join(context.relative_parts[..=index].iter().collect::<PathBuf>())
    })
}

pub(crate) fn domain_dir(context: &NativeRuleContext) -> Option<PathBuf> {
    context
        .relative_parts
        .first()
        .map(|domain| scope_root(context).join(domain))
}

pub(crate) fn leaf_dir(context: &NativeRuleContext) -> Option<PathBuf> {
    if context.scope != ROOT_SCOPE || context.relative_parts.len() < MINIMUM_DOMAIN_PARTS {
        return None;
    }
    let domain = scope_root(context).join(&context.relative_parts[0]);
    if context.relative_parts.len() < MINIMUM_SUBDOMAIN_PARTS
        || ROLE_NAMES.contains(&context.relative_parts[1].as_str())
        || context.relative_parts[1].ends_with(".py")
    {
        Some(domain)
    } else {
        Some(domain.join(&context.relative_parts[1]))
    }
}

pub(crate) fn mixed_domain(domain: &Path) -> bool {
    let entries = directory_entries(domain);
    entries.iter().any(|entry| {
        role_name(entry)
            || (entry.extension().and_then(|value| value.to_str()) == Some(PYTHON_EXTENSION)
                && ROLE_FILES.contains(&file_name(entry)))
    }) && !named_subdomains(domain).is_empty()
}

pub(crate) fn named_subdomains(domain: &Path) -> Vec<PathBuf> {
    directory_entries(domain)
        .into_iter()
        .filter(|entry| {
            !role_name(entry)
                && file_name(entry) != PYTHON_CACHE
                && entry.is_dir()
                && !recursive_python(entry).is_empty()
        })
        .collect()
}

pub(crate) fn prefix_candidates(root: &Path) -> Vec<PathBuf> {
    directory_entries(root)
        .into_iter()
        .filter(|entry| {
            let name = file_name(entry);
            !name.starts_with('_')
                && !role_name(entry)
                && name != LEGACY_HELPERS
                && name != PYTHON_CACHE
                && name.contains('_')
                && python_identifier(name)
        })
        .collect()
}

pub(crate) fn prefix_groups(root: &Path) -> Vec<(String, Vec<String>)> {
    let mut grouped: BTreeMap<String, Vec<String>> = BTreeMap::new();
    for entry in prefix_candidates(root) {
        if !entry.is_dir() || recursive_python(&entry).is_empty() {
            continue;
        }
        let name = file_name(&entry);
        let Some((prefix, suffix)) = name.split_once('_') else {
            continue;
        };
        if prefix.is_empty() || suffix.is_empty() {
            continue;
        }
        grouped
            .entry(prefix.to_owned())
            .or_default()
            .push(name.to_owned());
    }
    grouped
        .into_iter()
        .map(|(prefix, mut names)| {
            names.sort();
            (prefix, names)
        })
        .collect()
}

pub(crate) fn main_entries(leaf: &Path) -> Vec<PathBuf> {
    recursive_python(&leaf.join(MAIN_ROLE))
        .into_iter()
        .filter(|path| file_name(path) != INIT_FILE)
        .collect()
}

pub(crate) fn direct_modules(path: &Path) -> Vec<PathBuf> {
    let mut paths: Vec<PathBuf> = directory_entries(path)
        .into_iter()
        .filter(|entry| {
            entry.extension().and_then(|value| value.to_str()) == Some(PYTHON_EXTENSION)
                && file_name(entry) != INIT_FILE
        })
        .collect();
    paths.sort();
    paths
}

pub(crate) fn recursive_python(path: &Path) -> Vec<PathBuf> {
    let mut paths = Vec::new();
    collect_python(path, &mut paths);
    paths.sort();
    paths
}

fn collect_python(path: &Path, paths: &mut Vec<PathBuf>) {
    for entry in directory_entries(path) {
        if entry.is_dir() {
            collect_python(&entry, paths);
        } else if entry.extension().and_then(|value| value.to_str()) == Some(PYTHON_EXTENSION) {
            paths.push(entry);
        }
    }
}

pub(crate) fn python_anchor(path: &Path) -> Option<PathBuf> {
    let init = path.join(INIT_FILE);
    if init.is_file() {
        return Some(init);
    }
    direct_modules(path)
        .into_iter()
        .next()
        .or_else(|| recursive_python(path).into_iter().next())
}

pub(crate) fn directory_entries(path: &Path) -> Vec<PathBuf> {
    fs::read_dir(path)
        .ok()
        .into_iter()
        .flatten()
        .filter_map(Result::ok)
        .map(|entry| entry.path())
        .collect()
}

pub(crate) fn scope_root(context: &NativeRuleContext) -> PathBuf {
    let relative = context
        .scope_roots
        .iter()
        .find_map(|(scope, root)| (scope == &context.scope).then_some(root))
        .cloned()
        .unwrap_or_default();
    Path::new(&context.repo_root).join(relative)
}

pub(crate) fn repository_path(context: &NativeRuleContext) -> PathBuf {
    Path::new(&context.repo_root).join(&context.repository_path)
}

pub(crate) fn role_name(path: &Path) -> bool {
    ROLE_NAMES.contains(&file_name(path))
}

pub(crate) fn forbidden_bucket(path: &Path) -> bool {
    role_name(path) || file_name(path) == LEGACY_HELPERS
}

pub(crate) fn file_name(path: &Path) -> &str {
    path.file_name()
        .and_then(|name| name.to_str())
        .unwrap_or("")
}

fn python_identifier(name: &str) -> bool {
    let mut chars = name.chars();
    chars
        .next()
        .is_some_and(|character| character == '_' || is_xid_start(character))
        && chars.all(|character| character == '_' || is_xid_continue(character))
}

pub(crate) fn natural_list(values: &[String]) -> String {
    match values {
        [] => String::new(),
        [value] => value.clone(),
        [first, second] => format!("{first} and {second}"),
        _ => format!(
            "{}, and {}",
            values[..values.len() - 1].join(", "),
            values.last().unwrap_or(&String::new())
        ),
    }
}
