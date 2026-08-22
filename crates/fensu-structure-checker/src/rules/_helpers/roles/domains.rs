//! Domain-shape rules: leaf-or-branch domains, role boundaries, and main/ entries.

use std::collections::{BTreeMap, BTreeSet};
use std::path;

use crate::constants;
use crate::models;

#[derive(Debug, Default)]
struct DirectoryContents {
    modules: BTreeSet<String>,
    directories: BTreeSet<String>,
}

pub(crate) fn check_domains(files: &[models::SourceFile]) -> Vec<models::Violation> {
    let Some(source_root) = source_root(files) else {
        return Vec::new();
    };
    let tree = directory_tree(files);
    let mut violations: Vec<models::Violation> = Vec::new();
    for domain in top_level_domains(&tree) {
        violations.extend(direct_module_violations(&source_root, &tree, &domain));
        violations.extend(domain_shape_violations(&source_root, &tree, &domain));
    }
    for directory in tree.keys() {
        violations.extend(role_boundary_violations(&source_root, &tree, directory));
        violations.extend(main_boundary_violations(&source_root, &tree, directory));
    }
    violations.sort_by(|left, right| left.sort_key().cmp(&right.sort_key()));
    violations.dedup_by(|left, right| left.sort_key() == right.sort_key());
    violations
}

fn source_root(files: &[models::SourceFile]) -> Option<String> {
    let first = files.first()?;
    Some(first.source_root_relative.clone())
}

fn directory_tree(files: &[models::SourceFile]) -> BTreeMap<String, DirectoryContents> {
    let mut tree: BTreeMap<String, DirectoryContents> = BTreeMap::new();
    for file in files {
        let components: Vec<&str> = file.source_relative.split('/').collect();
        let Some((name, directories)) = components.split_last() else {
            continue;
        };
        for index in 0..=directories.len() {
            let key = directories[..index].join("/");
            let contents = tree.entry(key).or_default();
            match directories.get(index) {
                Some(child) => {
                    contents.directories.insert((*child).to_owned());
                }
                None => {
                    contents.modules.insert((*name).to_owned());
                }
            }
        }
    }
    tree
}

fn top_level_domains(tree: &BTreeMap<String, DirectoryContents>) -> Vec<String> {
    let Some(root) = tree.get("") else {
        return Vec::new();
    };
    root.directories
        .iter()
        .filter(|name| {
            !is_role_container(name)
                && *name != constants::TESTS_DIRECTORY
                && *name != constants::BIN_DIRECTORY
        })
        .cloned()
        .collect()
}

fn is_role_container(name: &str) -> bool {
    constants::CONTAINER_DIRECTORY_NAMES.contains(&name)
}

fn subdomains(contents: &DirectoryContents) -> Vec<String> {
    contents
        .directories
        .iter()
        .filter(|name| !is_role_container(name) && *name != constants::TESTS_DIRECTORY)
        .cloned()
        .collect()
}

fn holds_role_content(contents: &DirectoryContents) -> bool {
    contents
        .directories
        .iter()
        .any(|name| is_role_container(name))
        || contents
            .modules
            .iter()
            .any(|name| name != constants::MOD_FILE && is_role_file(name))
}

fn is_role_file(name: &str) -> bool {
    constants::ROLE_FILE_NAMES.contains(&name)
}

fn direct_module_violations(
    source_root: &str,
    tree: &BTreeMap<String, DirectoryContents>,
    domain: &str,
) -> Vec<models::Violation> {
    let Some(contents) = tree.get(domain) else {
        return Vec::new();
    };
    contents
        .modules
        .iter()
        .filter(|name| {
            *name != constants::MOD_FILE
                && *name != constants::INLINE_TEST_HARNESS_FILE
                && !is_role_file(name)
        })
        .map(|name| {
            let relative = format!("{source_root}/{domain}/{name}");
            models::Violation::new(models::ViolationRequest {
                code: "RSR307",
                path: path::Path::new(&relative),
                line: None,
                message: "top-level domain holds an ad hoc direct module",
                remediation:
                    "move the module under a role boundary or into an owning named subdomain",
            })
        })
        .collect()
}

fn domain_shape_violations(
    source_root: &str,
    tree: &BTreeMap<String, DirectoryContents>,
    domain: &str,
) -> Vec<models::Violation> {
    let Some(contents) = tree.get(domain) else {
        return Vec::new();
    };
    let nested = subdomains(contents);
    if nested.is_empty() || !holds_role_content(contents) {
        return Vec::new();
    }
    let relative = format!("{source_root}/{domain}");
    vec![models::Violation::new(models::ViolationRequest {
        code: "RSR306",
        path: path::Path::new(&relative),
        line: None,
        message: format!(
            "top-level domain mixes direct role content with subdomains {}",
            nested.join(", ")
        ),
        remediation: "keep direct role content in a leaf domain, or move it into a named subdomain",
    })]
}

fn role_boundary_violations(
    source_root: &str,
    tree: &BTreeMap<String, DirectoryContents>,
    directory: &str,
) -> Vec<models::Violation> {
    if directory.is_empty() || inside_role_container(directory) {
        return Vec::new();
    }
    if directory.split('/').count() < constants::MIN_NESTED_PACKAGE_DEPTH {
        return Vec::new();
    }
    let Some(contents) = tree.get(directory) else {
        return Vec::new();
    };
    subdomains(contents)
        .iter()
        .map(|name| {
            let relative = format!("{source_root}/{directory}/{name}");
            models::Violation::new(models::ViolationRequest {
                code: "RSR305",
                path: path::Path::new(&relative),
                line: None,
                message: "nested package holds a feature subpackage outside a role boundary",
                remediation: "move the subpackage under _helpers/ or expose it through main/",
            })
        })
        .collect()
}

fn main_boundary_violations(
    source_root: &str,
    tree: &BTreeMap<String, DirectoryContents>,
    directory: &str,
) -> Vec<models::Violation> {
    if directory.is_empty() || inside_role_container(directory) {
        return Vec::new();
    }
    let Some(contents) = tree.get(directory) else {
        return Vec::new();
    };
    if !holds_role_content(contents) || !subdomains(contents).is_empty() {
        return Vec::new();
    }
    if holds_entry_module(tree, directory) {
        return Vec::new();
    }
    let relative = format!("{source_root}/{directory}");
    vec![models::Violation::new(models::ViolationRequest {
        code: "RSR309",
        path: path::Path::new(&relative),
        line: None,
        message: "leaf domain exposes no main/ entry module",
        remediation:
            "add a focused main/ entry, or move passive declarations to the domain that owns them",
    })]
}

fn holds_entry_module(tree: &BTreeMap<String, DirectoryContents>, directory: &str) -> bool {
    let main_directory = format!("{directory}/{}", constants::MAIN_DIRECTORY);
    tree.iter()
        .filter(|(key, _)| {
            **key == main_directory || key.starts_with(&format!("{main_directory}/"))
        })
        .any(|(_, contents)| holds_non_mod_module(contents))
}

fn holds_non_mod_module(contents: &DirectoryContents) -> bool {
    contents
        .modules
        .iter()
        .any(|name| name != constants::MOD_FILE)
}

fn inside_role_container(directory: &str) -> bool {
    directory
        .split('/')
        .any(|part| is_role_container(part) || part == constants::TESTS_DIRECTORY)
}
