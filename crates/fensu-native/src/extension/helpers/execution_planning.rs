//! Native file selection and deterministic execution-owner planning.

use std::collections::{BTreeMap, HashSet};

use globset::{GlobBuilder, GlobSet, GlobSetBuilder};
use pyo3::exceptions::PyValueError;
use pyo3::{pyfunction, PyResult};

use crate::extension::constants::{
    CUSTOM_FAMILY, FILE_OWNER, INIT_MODULE_FILE, PACKAGE_OWNER, RECURSIVE_GLOB, TEST_SCOPE,
};

type TargetTuple = (String, String, String, Vec<String>, bool);
type RuleTuple = (String, String, String);
type PlannedTargetTuple = (Vec<String>, Vec<(String, String)>);

#[pyfunction]
pub(crate) fn select_native_execution_files(
    paths: Vec<String>,
    includes: Vec<String>,
    excludes: Vec<String>,
) -> PyResult<(Option<Vec<usize>>, usize)> {
    if includes.is_empty() && excludes.is_empty() {
        return Ok((None, 0));
    }
    let include_set = build_patterns(&includes)?;
    let exclude_set = build_patterns(&excludes)?;
    for pattern in &includes {
        let matcher = build_patterns(std::slice::from_ref(pattern))?;
        if !paths.iter().any(|path| matcher.is_match(path)) {
            return Err(PyValueError::new_err(format!(
                "Evaluation include pattern matched no discovered Python files: {pattern}."
            )));
        }
    }
    let selected: Vec<usize> = paths
        .iter()
        .enumerate()
        .filter_map(|(index, path)| {
            let included = includes.is_empty() || include_set.is_match(path);
            (included && !exclude_set.is_match(path)).then_some(index)
        })
        .collect();
    if selected.is_empty() && !paths.is_empty() {
        return Err(PyValueError::new_err(
            "Evaluation configuration selects zero Python files; exclusions removed all targets.",
        ));
    }
    let excluded = paths.len().saturating_sub(selected.len());
    Ok((Some(selected), excluded))
}

#[pyfunction]
pub(crate) fn plan_native_execution_owners(
    targets: Vec<TargetTuple>,
    rules: Vec<RuleTuple>,
) -> Vec<PlannedTargetTuple> {
    let mut codes: Vec<Vec<String>> = vec![Vec::new(); targets.len()];
    let mut identities: Vec<Vec<(String, String)>> = vec![Vec::new(); targets.len()];
    for (code, family, owner) in rules {
        if owner == FILE_OWNER {
            for (index, target) in targets.iter().enumerate() {
                if target.4 && family_applies(&family, &target.1) {
                    codes[index].push(code.clone());
                    identities[index].push((code.clone(), format!("file\0{}", target.0)));
                }
            }
            continue;
        }
        let mut groups: BTreeMap<String, Vec<usize>> = BTreeMap::new();
        for (index, target) in targets.iter().enumerate() {
            if !target.4 || !family_applies(&family, &target.1) {
                continue;
            }
            if let Some(identity) = owner_identity(target, &owner) {
                groups.entry(identity).or_default().push(index);
            }
        }
        for (identity, indexes) in groups {
            let Some(anchor) = indexes
                .into_iter()
                .min_by_key(|index| anchor_key(&targets[*index], &owner))
            else {
                continue;
            };
            codes[anchor].push(code.clone());
            identities[anchor].push((code.clone(), identity));
        }
    }
    codes.into_iter().zip(identities).collect()
}

#[pyfunction]
pub(crate) fn partition_native_execution_targets(
    ordered_paths: Vec<String>,
    work_paths: Vec<String>,
) -> Vec<usize> {
    let work: HashSet<String> = work_paths.into_iter().collect();
    ordered_paths
        .iter()
        .enumerate()
        .filter_map(|(index, path)| work.contains(path).then_some(index))
        .collect()
}

fn build_patterns(patterns: &[String]) -> PyResult<GlobSet> {
    let mut builder = GlobSetBuilder::new();
    for pattern in patterns {
        let pattern = if pattern.contains('/') || pattern == RECURSIVE_GLOB {
            pattern.clone()
        } else {
            format!("{{{pattern},**/{pattern}}}")
        };
        let glob = GlobBuilder::new(&pattern)
            .literal_separator(true)
            .backslash_escape(false)
            .build()
            .map_err(|error| PyValueError::new_err(error.to_string()))?;
        builder.add(glob);
    }
    builder
        .build()
        .map_err(|error| PyValueError::new_err(error.to_string()))
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

fn owner_identity(target: &TargetTuple, owner: &str) -> Option<String> {
    let domain = target.3.first().filter(|part| !part.ends_with(".py"));
    let subdomain = target.3.get(1).filter(|part| {
        !part.ends_with(".py") && !matches!(part.as_str(), "main" | "_helpers" | "classes")
    });
    match owner {
        "project" => Some("project".to_owned()),
        "scope" => Some(format!("scope\0{}\0{}", target.1, target.2)),
        "package" => Some(format!(
            "package\0{}",
            target
                .0
                .rsplit_once('/')
                .map(|(parent, _)| parent)
                .unwrap_or(".")
        )),
        "domain" => domain.map(|domain| format!("domain\0{}\0{}\0{domain}", target.1, target.2)),
        "subdomain" => subdomain.map(|subdomain| {
            format!(
                "subdomain\0{}\0{}\0{}\0{subdomain}",
                target.1,
                target.2,
                domain.map(String::as_str).unwrap_or_default()
            )
        }),
        "leaf" => domain.map(|domain| {
            format!(
                "leaf\0{}\0{}\0{domain}\0{}",
                target.1,
                target.2,
                subdomain.map(String::as_str).unwrap_or_default()
            )
        }),
        _ => None,
    }
}

fn anchor_key<'a>(target: &'a TargetTuple, owner: &str) -> (bool, usize, &'a str) {
    let parts = &target.3;
    let domain = parts.first().is_some_and(|part| !part.ends_with(".py"));
    let subdomain = parts.get(1).is_some_and(|part| {
        !part.ends_with(".py") && !matches!(part.as_str(), "main" | "_helpers" | "classes")
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
    (!owner_init, parts.len(), target.0.as_str())
}
