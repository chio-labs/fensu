//! Traversal-root and arbitrary-glob preparation for repository observations.

use std::path::{Path, PathBuf};

use globset::{GlobBuilder, GlobMatcher};

use crate::snapshot::constants::REPOSITORY_ROOT_PATH;
use crate::snapshot::models::RepositoryObservationQuery;

pub(crate) fn traversal_roots(
    repo_root: &Path,
    queries: &[RepositoryObservationQuery],
) -> Vec<PathBuf> {
    let mut candidates = queries
        .iter()
        .filter(|query| {
            matches!(
                query.kind.as_str(),
                "glob" | "directory_entries" | "python_anchor"
            )
        })
        .filter_map(|query| existing_directory(repo_root, &query.relative_path))
        .collect::<Vec<_>>();
    candidates.sort();
    candidates.dedup();
    let mut roots: Vec<PathBuf> = Vec::new();
    for candidate in candidates {
        if roots.iter().any(|root| candidate.starts_with(root)) {
            continue;
        }
        roots.retain(|root| !root.starts_with(&candidate));
        roots.push(candidate);
    }
    roots
}

pub(crate) fn glob_matcher(pattern: &str) -> Option<GlobMatcher> {
    GlobBuilder::new(pattern)
        .literal_separator(true)
        .backslash_escape(false)
        .build()
        .ok()
        .map(|glob| glob.compile_matcher())
}

pub(crate) fn join_relative(root: &str, name: &str) -> String {
    if root == REPOSITORY_ROOT_PATH {
        name.to_owned()
    } else {
        format!("{root}/{name}")
    }
}

fn existing_directory(repo_root: &Path, relative: &str) -> Option<PathBuf> {
    let path = repo_root.join(relative);
    path.is_dir().then_some(path)
}
