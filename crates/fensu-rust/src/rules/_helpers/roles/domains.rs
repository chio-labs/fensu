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

pub(crate) fn check_domains(
    files: &[models::SourceFile],
    targets: &[models::WorkspaceTarget],
    ownership_depth: usize,
) -> Vec<models::Violation> {
    let Some(source_root) = source_root(files) else {
        return Vec::new();
    };
    let tree = directory_tree(files);
    let grouping_depth = ownership_depth.saturating_sub(2);
    let mut violations: Vec<models::Violation> = Vec::new();
    violations.extend(root_direct_module_violations(&source_root, &tree, targets));
    for group in grouping_roots(&tree, grouping_depth) {
        violations.extend(grouping_shape_violations(&source_root, &tree, &group));
        violations.extend(direct_module_violations(&source_root, &tree, &group));
    }
    for domain in domain_roots(&tree, grouping_depth) {
        violations.extend(direct_module_violations(&source_root, &tree, &domain));
        violations.extend(domain_shape_violations(&source_root, &tree, &domain));
    }
    for directory in tree.keys() {
        violations.extend(role_boundary_violations(
            &source_root,
            &tree,
            directory,
            grouping_depth,
        ));
        violations.extend(main_boundary_violations(
            &source_root,
            &tree,
            directory,
            grouping_depth,
        ));
    }
    violations.sort_by(|left, right| left.sort_key().cmp(&right.sort_key()));
    violations.dedup_by(|left, right| left.sort_key() == right.sort_key());
    violations
}

fn root_direct_module_violations(
    source_root: &str,
    tree: &BTreeMap<String, DirectoryContents>,
    targets: &[models::WorkspaceTarget],
) -> Vec<models::Violation> {
    let Some(root) = tree.get("") else {
        return Vec::new();
    };
    let entry_files = targets
        .iter()
        .filter(|target| !target.test)
        .filter(|target| target.source_root.ends_with(path::Path::new(source_root)))
        .filter(|target| target.entry_path.parent() == Some(target.source_root.as_path()))
        .filter_map(|target| target.entry_path.file_name())
        .filter_map(|name| name.to_str())
        .collect::<BTreeSet<_>>();
    root.modules
        .iter()
        .filter(|name| {
            !entry_files.contains(name.as_str())
                && name.as_str() != constants::INLINE_TEST_HARNESS_FILE
                && !is_role_file(name)
        })
        .map(|name| {
            let relative = format!("{source_root}/{name}");
            models::Violation::new(models::ViolationRequest {
                code: "RSR307",
                path: path::Path::new(&relative),
                line: None,
                message: "runtime source root holds an ad hoc direct module",
                remediation: "keep Cargo entry files and role files at the source root; move behavior into an owning domain",
            })
        })
        .collect()
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

fn grouping_roots(
    tree: &BTreeMap<String, DirectoryContents>,
    grouping_depth: usize,
) -> Vec<String> {
    if grouping_depth == 0 {
        return Vec::new();
    }
    tree.keys()
        .filter(|directory| {
            let depth = path_depth(directory);
            depth > 0 && depth <= grouping_depth && !inside_role_container(directory)
        })
        .cloned()
        .collect()
}

fn ownership_roots(
    tree: &BTreeMap<String, DirectoryContents>,
    grouping_depth: usize,
) -> Vec<String> {
    if grouping_depth == 0 {
        return vec![String::new()];
    }
    tree.keys()
        .filter(|directory| {
            path_depth(directory) == grouping_depth && !inside_role_container(directory)
        })
        .cloned()
        .collect()
}

fn domain_roots(tree: &BTreeMap<String, DirectoryContents>, grouping_depth: usize) -> Vec<String> {
    let mut domains: Vec<String> = Vec::new();
    for root in ownership_roots(tree, grouping_depth) {
        let Some(contents) = tree.get(&root) else {
            continue;
        };
        domains.extend(
            contents
                .directories
                .iter()
                .filter(|name| {
                    !is_role_container(name)
                        && *name != constants::TESTS_DIRECTORY
                        && *name != constants::BIN_DIRECTORY
                })
                .map(|name| join_path(&root, name)),
        );
    }
    domains.sort();
    domains
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

fn grouping_shape_violations(
    source_root: &str,
    tree: &BTreeMap<String, DirectoryContents>,
    group: &str,
) -> Vec<models::Violation> {
    let Some(contents) = tree.get(group) else {
        return Vec::new();
    };
    if !holds_role_content(contents) {
        return Vec::new();
    }
    let relative = format!("{source_root}/{group}");
    vec![models::Violation::new(models::ViolationRequest {
        code: "RSR306",
        path: path::Path::new(&relative),
        line: None,
        message: "structural ownership group contains direct role content".to_owned(),
        remediation: "move role content beneath the required domain level",
    })]
}

fn role_boundary_violations(
    source_root: &str,
    tree: &BTreeMap<String, DirectoryContents>,
    directory: &str,
    grouping_depth: usize,
) -> Vec<models::Violation> {
    if directory.is_empty() || inside_role_container(directory) {
        return Vec::new();
    }
    if path_depth(directory) < grouping_depth + constants::MIN_NESTED_PACKAGE_DEPTH {
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
    grouping_depth: usize,
) -> Vec<models::Violation> {
    if directory.is_empty()
        || path_depth(directory) <= grouping_depth
        || inside_role_container(directory)
    {
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

fn path_depth(directory: &str) -> usize {
    if directory.is_empty() {
        0
    } else {
        directory.split('/').count()
    }
}

fn join_path(parent: &str, child: &str) -> String {
    if parent.is_empty() {
        child.to_owned()
    } else {
        format!("{parent}/{child}")
    }
}
