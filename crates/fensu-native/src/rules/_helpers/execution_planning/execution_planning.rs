//! Shared native rule applicability and execution-owner planning internals.

use std::collections::BTreeMap;

use crate::rules::models::{NativeExecutionPlan, NativeExecutionRule, NativeExecutionTarget};

const CUSTOM_FAMILY: &str = "custom";
const FILE_OWNER: &str = "file";
const INIT_MODULE_FILE: &str = "__init__.py";
const PACKAGE_OWNER: &str = "package";
const RECOGNIZED_ROLE_DIRECTORIES: &[&str] = &[
    "main",
    "_helpers",
    "classes",
    "models",
    "types",
    "constants",
    "exceptions",
];
const TEST_SCOPE: &str = "test";

pub(crate) fn build_execution_plan(
    targets: &[NativeExecutionTarget],
    rules: &[NativeExecutionRule],
) -> Result<Vec<NativeExecutionPlan>, String> {
    let mut plans: Vec<NativeExecutionPlan> = vec![NativeExecutionPlan::default(); targets.len()];
    for rule in rules {
        let applicable: Vec<usize> = targets
            .iter()
            .enumerate()
            .filter_map(|(index, target)| {
                (target.direct && family_applies(&rule.family, &target.scope)).then_some(index)
            })
            .collect();
        if applicable.is_empty() {
            continue;
        }
        if rule.owner == FILE_OWNER {
            for index in applicable {
                plans[index].codes.push(rule.code.clone());
                plans[index].identities.push((
                    rule.code.clone(),
                    format!("file\0{}", targets[index].repository_path),
                ));
            }
            continue;
        }
        if !is_recognized_owner(&rule.owner) {
            return Err(format!(
				"Selected rule {} has applicable files but execution owner '{}' produced no targets.",
				rule.code, rule.owner
			));
        }

        let mut groups: BTreeMap<String, Vec<usize>> = BTreeMap::new();
        for index in applicable {
            if let Some(identity) = owner_identity(&targets[index], &rule.owner) {
                groups.entry(identity).or_default().push(index);
            }
        }
        if groups.is_empty() {
            continue;
        }
        for (identity, indexes) in groups {
            let Some(anchor) = indexes
                .into_iter()
                .min_by_key(|index| anchor_key(&targets[*index], &rule.owner))
            else {
                continue;
            };
            plans[anchor].codes.push(rule.code.clone());
            plans[anchor].identities.push((rule.code.clone(), identity));
        }
    }
    Ok(plans)
}

fn is_recognized_owner(owner: &str) -> bool {
    matches!(
        owner,
        "project" | "scope" | PACKAGE_OWNER | "domain" | "subdomain" | "leaf"
    )
}

fn family_applies(family: &str, scope: &str) -> bool {
    family == CUSTOM_FAMILY
        || if scope == TEST_SCOPE {
            matches!(family, "annotations" | "tests")
        } else {
            matches!(
                family,
                "annotations" | "hygiene" | "layers" | "naming" | "roles" | "shape"
            )
        }
}

fn owner_identity(target: &NativeExecutionTarget, owner: &str) -> Option<String> {
    let domain = target
        .relative_parts
        .first()
        .filter(|part| !part.ends_with(".py"));
    let subdomain = target.relative_parts.get(1).filter(|part| {
        !part.ends_with(".py") && !RECOGNIZED_ROLE_DIRECTORIES.contains(&part.as_str())
    });
    match owner {
        "project" => Some("project".to_owned()),
        "scope" => Some(format!("scope\0{}\0{}", target.scope, target.root)),
        PACKAGE_OWNER => Some(format!(
            "package\0{}",
            target
                .repository_path
                .rsplit_once('/')
                .map(|(parent, _)| parent)
                .unwrap_or(".")
        )),
        "domain" => {
            domain.map(|domain| format!("domain\0{}\0{}\0{domain}", target.scope, target.root))
        }
        "subdomain" => subdomain.map(|subdomain| {
            format!(
                "subdomain\0{}\0{}\0{}\0{subdomain}",
                target.scope,
                target.root,
                domain.map(String::as_str).unwrap_or_default()
            )
        }),
        "leaf" => domain.map(|domain| {
            format!(
                "leaf\0{}\0{}\0{domain}\0{}",
                target.scope,
                target.root,
                subdomain.map(String::as_str).unwrap_or_default()
            )
        }),
        _ => None,
    }
}

fn anchor_key<'a>(target: &'a NativeExecutionTarget, owner: &str) -> (bool, usize, &'a str) {
    let parts = &target.relative_parts;
    let domain = parts.first().is_some_and(|part| !part.ends_with(".py"));
    let subdomain = parts.get(1).is_some_and(|part| {
        !part.ends_with(".py") && !RECOGNIZED_ROLE_DIRECTORIES.contains(&part.as_str())
    });
    let expected_depth = match owner {
        "scope" => Some(1),
        "domain" => Some(2),
        "subdomain" => Some(3),
        "leaf" if domain => Some(if subdomain { 3 } else { 2 }),
        _ => None,
    };
    let mut owner_init = expected_depth.is_some_and(|depth| {
        parts.len() == depth && parts.last().is_some_and(|part| part == INIT_MODULE_FILE)
    });
    if owner == PACKAGE_OWNER {
        owner_init = parts.last().is_some_and(|part| part == INIT_MODULE_FILE);
    }
    (!owner_init, parts.len(), target.repository_path.as_str())
}
