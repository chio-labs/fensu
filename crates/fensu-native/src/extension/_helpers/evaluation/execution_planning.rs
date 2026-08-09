//! Native file selection and deterministic execution-owner planning.

use std::collections::HashSet;

use globset::{GlobBuilder, GlobSet, GlobSetBuilder};
use pyo3::exceptions::PyValueError;
use pyo3::{pyfunction, PyResult};

use crate::extension::constants::RECURSIVE_GLOB;
use crate::rules::main::plan_execution_owners::plan_execution_owners;
use crate::rules::models::{NativeExecutionRule, NativeExecutionTarget};

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
) -> PyResult<Vec<PlannedTargetTuple>> {
    let native_targets: Vec<NativeExecutionTarget> = targets
        .into_iter()
        .map(
            |(repository_path, scope, root, relative_parts, direct)| NativeExecutionTarget {
                repository_path,
                scope,
                root,
                relative_parts,
                direct,
            },
        )
        .collect();
    let native_rules: Vec<NativeExecutionRule> = rules
        .into_iter()
        .map(|(code, family, owner)| NativeExecutionRule::new(code, family, owner))
        .collect();
    let plans =
        plan_execution_owners(&native_targets, &native_rules).map_err(PyValueError::new_err)?;
    Ok(plans
        .into_iter()
        .map(|plan| (plan.codes, plan.identities))
        .collect())
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
