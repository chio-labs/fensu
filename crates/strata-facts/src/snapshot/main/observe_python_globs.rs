//! Batch ordered `*.py` repository glob observations behind one native boundary.

use std::path::Path;

use crate::snapshot::helpers::python_globs::python_paths;
use crate::snapshot::helpers::repository_paths::{
    repository_relative_value, resolve_allow_missing,
};
use crate::snapshot::models::{RepositoryPythonGlobAnswer, RepositoryPythonGlobQuery};

/// Observe direct or recursive `*.py` matches in filesystem iteration order.
pub fn observe_python_globs(
    repo_root: &Path,
    queries: &[RepositoryPythonGlobQuery],
) -> Vec<Option<RepositoryPythonGlobAnswer>> {
    queries
        .iter()
        .map(|query| observe_query(repo_root, query))
        .collect()
}

fn observe_query(
    repo_root: &Path,
    query: &RepositoryPythonGlobQuery,
) -> Option<RepositoryPythonGlobAnswer> {
    let lexical_path = repo_root.join(&query.relative_path);
    let resolved_path = resolve_allow_missing(&lexical_path)?;
    let dependency_path = repository_relative_value(repo_root, &resolved_path)?;
    let paths = python_paths(&lexical_path, query.recursive);
    let answer: Option<Vec<String>> = paths
        .iter()
        .map(|path| repository_relative_value(repo_root, path))
        .collect();
    Some(RepositoryPythonGlobAnswer {
        dependency_path,
        answer: answer?,
    })
}
