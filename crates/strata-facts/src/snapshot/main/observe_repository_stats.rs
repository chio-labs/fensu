//! Batch live repository metadata observations behind one native boundary.

use std::path::Path;

use crate::snapshot::helpers::repository_paths::{
    repository_relative_value, resolve_allow_missing,
};
use crate::snapshot::models::{RepositoryStatAnswer, RepositoryStatKind, RepositoryStatQuery};

/// Observe repository metadata in query order, leaving ambiguous paths unsupported.
pub fn observe_repository_stats(
    repo_root: &Path,
    queries: &[RepositoryStatQuery],
) -> Vec<Option<RepositoryStatAnswer>> {
    queries
        .iter()
        .map(|query| observe_query(repo_root, query))
        .collect()
}

fn observe_query(repo_root: &Path, query: &RepositoryStatQuery) -> Option<RepositoryStatAnswer> {
    let lexical_path = repo_root.join(&query.relative_path);
    let resolved_path = resolve_allow_missing(&lexical_path)?;
    let dependency_path = repository_relative_value(repo_root, &resolved_path)?;
    let answer = match query.kind {
        RepositoryStatKind::Exists => resolved_path.exists(),
        RepositoryStatKind::IsFile => resolved_path.is_file(),
        RepositoryStatKind::IsDir => resolved_path.is_dir(),
    };
    Some(RepositoryStatAnswer {
        dependency_path,
        answer,
    })
}
