//! Domain ownership inferred from transitive helper consumers.

use std::collections::BTreeSet;

use crate::constants;
use crate::models;
use crate::rules::_helpers::imports::reference_paths;

struct ModuleNode<'a> {
    file: &'a models::SourceFile,
    path: Vec<String>,
    domain: Option<String>,
    helper_owner: Option<String>,
}

pub(crate) fn check(
    crate_dir: &std::path::Path,
    package_name: Option<&str>,
    files: &[models::SourceFile],
) -> Vec<models::Violation> {
    let package = package_name
        .or_else(|| crate_dir.file_name().and_then(|name| name.to_str()))
        .unwrap_or_default()
        .replace('-', "_");
    let nodes = module_nodes(files, &package);
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
        let Some(consumer) = external_domains.iter().next() else {
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
                "helper owned by {owner} is consumed transitively only by the {consumer} domain"
            ),
            remediation: "move the helper and its private support chain into the consuming domain",
        }));
    }
    violations
}

fn module_nodes<'a>(files: &'a [models::SourceFile], package: &str) -> Vec<ModuleNode<'a>> {
    files
        .iter()
        .map(|file| {
            let parts = source_parts(file);
            let domain = source_domain(parts.first());
            let helper_owner = match parts.as_slice() {
                [owner, role, ..] if role == constants::HELPERS_DIRECTORY => Some(owner.clone()),
                _ => None,
            };
            ModuleNode {
                file,
                path: reference_paths::module_path(package, &file.relative),
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

fn source_parts(file: &models::SourceFile) -> Vec<String> {
    file.relative
        .split_once("/src/")
        .map(|(_, inside)| inside)
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
        let Ok(syntax) = syn::parse_file(&node.file.source) else {
            continue;
        };
        for (target, _) in reference_paths::collect(&syntax, &node.file.source, package) {
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
