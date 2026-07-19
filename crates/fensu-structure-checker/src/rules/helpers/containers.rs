//! Container rules: bounded role containers, role placement, entry shape.

use std::collections::BTreeMap;

use syn::spanned::Spanned;

use crate::constants;
use crate::models;
use crate::types::FileKind;

pub(crate) fn check_containers(files: &[models::SourceFile]) -> Vec<models::Violation> {
    let mut violations: Vec<models::Violation> = Vec::new();
    let mut direct_modules: BTreeMap<String, usize> = BTreeMap::new();
    let mut bucket_modules: BTreeMap<String, usize> = BTreeMap::new();
    for file in files {
        let Some((container, remainder)) = container_split(&file.relative) else {
            continue;
        };
        let depth = remainder.split('/').count();
        if depth > constants::MAX_CONTAINER_COMPONENT_DEPTH {
            violations.push(container_violation(
                &container,
                "nests modules beyond one grouping level",
            ));
            continue;
        }
        if depth == 1 && remainder != constants::MOD_FILE {
            *direct_modules.entry(container).or_insert(0) += 1;
            continue;
        }
        if depth == constants::MAX_CONTAINER_COMPONENT_DEPTH {
            *bucket_modules.entry(container).or_insert(0) += 1;
        }
    }
    let containers: Vec<String> = direct_modules
        .keys()
        .chain(bucket_modules.keys())
        .cloned()
        .collect();
    for container in containers {
        violations.extend(container_budget_violations(
            &container,
            direct_modules.get(&container).copied().unwrap_or(0),
            bucket_modules.get(&container).copied().unwrap_or(0),
        ));
    }
    violations.dedup_by(|left, right| left.sort_key() == right.sort_key());
    violations
}

pub(crate) fn check_file(
    file: &models::SourceFile,
    syntax: &syn::File,
    kind: FileKind,
) -> Vec<models::Violation> {
    if kind != FileKind::ModuleFile {
        return Vec::new();
    }
    if file.has_directory(constants::MAIN_DIRECTORY) {
        return check_entry_shape(file, syntax);
    }
    if file.has_directory(constants::HELPERS_DIRECTORY) {
        return Vec::new();
    }
    if constants::ROLE_FILE_NAMES.contains(&file.file_name()) {
        return Vec::new();
    }
    vec![models::Violation::new(
        "RSR304",
        file.relative_path(),
        None,
        "implementation module outside a role container",
        "move the module under the domain's helpers/ or main/ container",
    )]
}

fn check_entry_shape(file: &models::SourceFile, syntax: &syn::File) -> Vec<models::Violation> {
    let mut violations: Vec<models::Violation> = Vec::new();
    let mut visible_functions: usize = 0;
    let mut private_functions: usize = 0;
    for item in &syntax.items {
        match item {
            syn::Item::Use(_) => {}
            syn::Item::Fn(item_fn) => match item_fn.vis {
                syn::Visibility::Inherited => private_functions += 1,
                _ => visible_functions += 1,
            },
            other => violations.push(models::Violation::new(
                "RSR401",
                file.relative_path(),
                Some(other.span().start().line),
                "entry modules may contain only imports and functions",
                "move declarations into the domain's role files",
            )),
        }
    }
    if visible_functions != 1 {
        violations.push(models::Violation::new(
            "RSR401",
            file.relative_path(),
            None,
            format!("entry module exposes {visible_functions} functions"),
            "keep exactly one visible entry function per entry module",
        ));
    }
    if private_functions > constants::MAX_ENTRY_PRIVATE_FUNCTIONS {
        violations.push(models::Violation::new(
            "RSR401",
            file.relative_path(),
            None,
            format!("entry module defines {private_functions} private functions"),
            "move phase logic into the domain's helpers/ container",
        ));
    }
    violations
}

fn container_split(relative: &str) -> Option<(String, String)> {
    let (_, inside) = relative.split_once("/src/")?;
    let components: Vec<&str> = inside.split('/').collect();
    let position = components
        .iter()
        .position(|part| constants::CONTAINER_DIRECTORY_NAMES.contains(part))?;
    let remainder_parts = components.get(position + 1..)?;
    if remainder_parts.is_empty() {
        return None;
    }
    let prefix = relative.trim_end_matches(&format!("/{}", remainder_parts.join("/")));
    Some((prefix.to_owned(), remainder_parts.join("/")))
}

fn container_budget_violations(
    container: &str,
    direct: usize,
    buckets: usize,
) -> Vec<models::Violation> {
    let mut violations: Vec<models::Violation> = Vec::new();
    let is_main = container.ends_with(constants::MAIN_DIRECTORY);
    let limit = match is_main {
        true => constants::MAX_MAIN_CONTAINER_MODULES,
        false => constants::MAX_HELPER_CONTAINER_MODULES,
    };
    if direct > limit {
        violations.push(container_violation(
            container,
            &format!("holds {direct} direct modules; the limit is {limit}"),
        ));
    }
    if direct > 0 && buckets > 0 {
        violations.push(container_violation(
            container,
            "mixes direct modules with grouped buckets",
        ));
    }
    violations
}

fn container_violation(container: &str, detail: &str) -> models::Violation {
    let code = match container.ends_with(constants::MAIN_DIRECTORY) {
        true => "RSR302",
        false => "RSR301",
    };
    models::Violation::new(
        code,
        std::path::Path::new(container),
        None,
        format!("container {detail}"),
        "keep containers flat and bounded, or group every module one level deep",
    )
}
