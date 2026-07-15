//! Batch repository source and namespace observations behind one native boundary.

use std::fs;
use std::path::Path;

use sha2::{Digest, Sha256};

use crate::snapshot::helpers::python_globs::python_anchor;
use crate::snapshot::helpers::repository_paths::{
    repository_relative_value, resolve_allow_missing,
};
use crate::snapshot::models::{
    RepositoryContextAnswer, RepositoryContextKind, RepositoryContextQuery,
};

/// Observe source identities, directory entries, and Python anchors in query order.
pub fn observe_repository_contexts(
    repo_root: &Path,
    queries: &[RepositoryContextQuery],
) -> Vec<Option<RepositoryContextAnswer>> {
    queries
        .iter()
        .map(|query| observe_query(repo_root, query))
        .collect()
}

fn observe_query(
    repo_root: &Path,
    query: &RepositoryContextQuery,
) -> Option<RepositoryContextAnswer> {
    let lexical_path = repo_root.join(&query.relative_path);
    let resolved_path = resolve_allow_missing(&lexical_path)?;
    let dependency_path = repository_relative_value(repo_root, &resolved_path)?;
    let mut source_answer: Option<String> = None;
    let mut path_answer: Vec<String> = Vec::new();
    match query.kind {
        RepositoryContextKind::Source => {
            source_answer = fs::read(lexical_path)
                .ok()
                .map(|content| hex::encode(Sha256::digest(content)));
        }
        RepositoryContextKind::DirectoryEntries => {
            let entries = fs::read_dir(lexical_path).ok()?;
            let paths = entries
                .map(|entry| entry.map(|value| value.path()))
                .collect::<Result<Vec<_>, _>>()
                .ok()?;
            path_answer = paths
                .iter()
                .map(|path| repository_relative_value(repo_root, path))
                .collect::<Option<Vec<_>>>()?;
        }
        RepositoryContextKind::PythonAnchor => {
            path_answer = python_anchor(&lexical_path)
                .iter()
                .map(|path| repository_relative_value(repo_root, path))
                .collect::<Option<Vec<_>>>()?;
        }
    }
    Some(RepositoryContextAnswer {
        dependency_path,
        source_answer,
        path_answer,
    })
}
