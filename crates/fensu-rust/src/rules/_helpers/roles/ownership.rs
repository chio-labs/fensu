//! Domain ownership inferred from transitive helper consumers.

use std::collections::BTreeSet;

use crate::constants;
use crate::models;
use crate::rules::_helpers::imports::reference_paths;

struct ModuleNode<'a> {
    file: &'a models::SourceFile,
    path: Vec<String>,
    domain: Option<(String, String)>,
    helper_owner: Option<(String, String)>,
}

pub(crate) fn check(
    crate_dir: &std::path::Path,
    package_name: Option<&str>,
    files: &[models::SourceFile],
    ownership_roots: &[String],
) -> Vec<models::Violation> {
    let package = package_name
        .or_else(|| crate_dir.file_name().and_then(|name| name.to_str()))
        .unwrap_or_default()
        .replace('-', "_");
    let nodes = module_nodes(files, &package, ownership_roots);
    let consumers = consumer_graph(&nodes, &package);
    let mut violations: Vec<models::Violation> = Vec::new();
    for (index, node) in nodes.iter().enumerate() {
        let Some(owner) = &node.helper_owner else {
            continue;
        };
        let reachable = transitive_consumers(index, &consumers);
        let external_domains = reachable
            .iter()
            .filter_map(|consumer| nodes[*consumer].domain.as_ref())
            .filter(|domain| *domain != owner)
            .cloned()
            .collect::<BTreeSet<_>>();
        let local_consumer = reachable.iter().any(|consumer| {
            nodes[*consumer].domain.as_ref() == Some(owner)
                && nodes[*consumer].helper_owner.is_none()
        });
        if external_domains.len() != 1 {
            continue;
        }
        let Some((_, consumer)) = external_domains.iter().next() else {
            continue;
        };
        if local_consumer {
            continue;
        }
        violations.push(models::Violation::new(models::ViolationRequest {
            code: "RSR310",
            path: node.file.relative_path(),
            line: None,
            message: format!(
                "helper owned by {} is consumed transitively only by the {consumer} domain",
                owner.1
            ),
            remediation: "move the helper and its private support chain into the consuming domain",
        }));
    }
    violations
}

fn module_nodes<'a>(
    files: &'a [models::SourceFile],
    package: &str,
    ownership_roots: &[String],
) -> Vec<ModuleNode<'a>> {
    files
        .iter()
        .map(|file| {
            let parts = ownership_parts(file, ownership_roots);
            let ownership_root = file.ownership_root(ownership_roots);
            let domain = ownership_root.clone().zip(source_domain(parts.first()));
            let helper_owner = parts.first().zip(parts.get(1)).and_then(|(owner, role)| {
                (role == constants::HELPERS_DIRECTORY)
                    .then(|| (ownership_root.clone().unwrap_or_default(), owner.clone()))
            });
            ModuleNode {
                file,
                path: reference_paths::module_path(package, file),
                domain,
                helper_owner,
            }
        })
        .collect()
}

fn source_domain(part: Option<&String>) -> Option<String> {
    match part {
        Some(part) if !is_root_role(part) => Some(part.clone()),
        _ => None,
    }
}

fn ownership_parts(file: &models::SourceFile, ownership_roots: &[String]) -> Vec<String> {
    file.ownership_relative(ownership_roots)
        .unwrap_or_default()
        .split('/')
        .take_while(|part| !part.ends_with(".rs"))
        .map(str::to_owned)
        .collect()
}

fn is_root_role(part: &str) -> bool {
    matches!(part, constants::BIN_DIRECTORY | constants::TESTS_DIRECTORY)
}

fn consumer_graph(nodes: &[ModuleNode<'_>], package: &str) -> Vec<BTreeSet<usize>> {
    let mut consumers = vec![BTreeSet::new(); nodes.len()];
    for (consumer, node) in nodes.iter().enumerate() {
        let Some(syntax) = node.file.syntax.file.as_ref() else {
            continue;
        };
        for (target, _) in reference_paths::collect(syntax, &node.file.source, package) {
            let Some(owner) = referenced_module(nodes, &target) else {
                continue;
            };
            if owner != consumer {
                let _ = consumers[owner].insert(consumer);
            }
        }
    }
    consumers
}

fn referenced_module(nodes: &[ModuleNode<'_>], target: &[String]) -> Option<usize> {
    nodes
        .iter()
        .enumerate()
        .filter(|(_, node)| target.starts_with(&node.path))
        .max_by_key(|(_, node)| node.path.len())
        .map(|(index, _)| index)
}

fn transitive_consumers(start: usize, consumers: &[BTreeSet<usize>]) -> BTreeSet<usize> {
    let mut reachable: BTreeSet<usize> = BTreeSet::new();
    let mut pending = consumers[start].iter().copied().collect::<Vec<_>>();
    while let Some(next) = pending.pop() {
        if !reachable.insert(next) {
            continue;
        }
        pending.extend(consumers[next].iter().copied());
    }
    reachable
}
