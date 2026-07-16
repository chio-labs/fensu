//! Python-callable bindings over native repository observation entries.

use std::ffi::OsString;
use std::path::PathBuf;

use pyo3::{pyfunction, Python};

use crate::snapshot::main::hash_files::hash_files;
use crate::snapshot::main::observe_python_globs::observe_python_globs as observe_globs;
use crate::snapshot::main::observe_repository_contexts::observe_repository_contexts as observe_contexts;
use crate::snapshot::main::observe_repository_stats::observe_repository_stats as observe_stats;
use crate::snapshot::main::walk_python_files::walk_python_files as snapshot_walk;
use crate::snapshot::models::{
    RepositoryContextKind, RepositoryContextQuery, RepositoryPythonGlobQuery, RepositoryStatKind,
    RepositoryStatQuery,
};

type WalkedEntryRow = (PathBuf, Option<PathBuf>, Option<Vec<OsString>>);

#[pyfunction]
pub(crate) fn walk_python_files(py: Python<'_>, roots: Vec<PathBuf>) -> Vec<Vec<WalkedEntryRow>> {
    let walked = py.detach(move || snapshot_walk(&roots));
    walked
        .into_iter()
        .map(|entries| {
            entries
                .into_iter()
                .map(|entry| {
                    (
                        entry.entry_path,
                        entry.canonical_path,
                        entry.root_relative_parts,
                    )
                })
                .collect()
        })
        .collect()
}

#[pyfunction]
pub(crate) fn hash_source_files(py: Python<'_>, paths: Vec<PathBuf>) -> Vec<Option<String>> {
    py.detach(move || hash_files(&paths))
}

type RepositoryStatRow = Option<(String, bool)>;

#[pyfunction]
pub(crate) fn observe_repository_stats(
    py: Python<'_>,
    repo_root: PathBuf,
    queries: Vec<(PathBuf, String)>,
) -> Vec<RepositoryStatRow> {
    let prepared: Vec<Option<RepositoryStatQuery>> = queries
        .into_iter()
        .map(|(relative_path, kind)| {
            let kind = match kind.as_str() {
                "exists" => RepositoryStatKind::Exists,
                "is_file" => RepositoryStatKind::IsFile,
                "is_dir" => RepositoryStatKind::IsDir,
                _ => return None,
            };
            Some(RepositoryStatQuery {
                relative_path,
                kind,
            })
        })
        .collect();
    py.detach(move || {
        let supported: Vec<RepositoryStatQuery> = prepared
            .iter()
            .filter_map(|query| {
                query.as_ref().map(|query| RepositoryStatQuery {
                    relative_path: query.relative_path.clone(),
                    kind: query.kind,
                })
            })
            .collect();
        let mut answers = observe_stats(&repo_root, &supported).into_iter();
        prepared
            .into_iter()
            .map(|query| {
                query?;
                answers
                    .next()
                    .flatten()
                    .map(|answer| (answer.dependency_path, answer.answer))
            })
            .collect()
    })
}

type RepositoryGlobRow = Option<(String, Vec<String>)>;

#[pyfunction]
pub(crate) fn observe_repository_python_globs(
    py: Python<'_>,
    repo_root: PathBuf,
    queries: Vec<(PathBuf, bool)>,
) -> Vec<RepositoryGlobRow> {
    let prepared: Vec<RepositoryPythonGlobQuery> = queries
        .into_iter()
        .map(|(relative_path, recursive)| RepositoryPythonGlobQuery {
            relative_path,
            recursive,
        })
        .collect();
    py.detach(move || {
        observe_globs(&repo_root, &prepared)
            .into_iter()
            .map(|answer| answer.map(|answer| (answer.dependency_path, answer.answer)))
            .collect()
    })
}

type RepositoryContextRow = Option<(String, Option<String>, Vec<String>)>;

#[pyfunction]
pub(crate) fn observe_repository_contexts(
    py: Python<'_>,
    repo_root: PathBuf,
    queries: Vec<(PathBuf, String)>,
) -> Vec<RepositoryContextRow> {
    let prepared: Vec<Option<RepositoryContextQuery>> = queries
        .into_iter()
        .map(|(relative_path, kind)| {
            let kind = match kind.as_str() {
                "source" => RepositoryContextKind::Source,
                "directory_entries" => RepositoryContextKind::DirectoryEntries,
                "python_anchor" => RepositoryContextKind::PythonAnchor,
                _ => return None,
            };
            Some(RepositoryContextQuery {
                relative_path,
                kind,
            })
        })
        .collect();
    py.detach(move || {
        let supported: Vec<RepositoryContextQuery> = prepared
            .iter()
            .filter_map(|query| {
                query.as_ref().map(|query| RepositoryContextQuery {
                    relative_path: query.relative_path.clone(),
                    kind: query.kind,
                })
            })
            .collect();
        let mut answers = observe_contexts(&repo_root, &supported).into_iter();
        prepared
            .into_iter()
            .map(|query| {
                query?;
                answers.next().flatten().map(|answer| {
                    (
                        answer.dependency_path,
                        answer.source_answer,
                        answer.path_answer,
                    )
                })
            })
            .collect()
    })
}
