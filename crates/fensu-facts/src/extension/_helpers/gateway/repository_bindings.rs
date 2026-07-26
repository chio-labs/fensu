//! Python-callable bindings over native repository observation entries.

use std::ffi::OsString;
use std::path::PathBuf;

use pyo3::{pyfunction, Python};

use crate::snapshot::main::hash_files::hash_files;
use crate::snapshot::main::walk_python_files::walk_python_files as snapshot_walk;

type WalkedEntryRow = (PathBuf, Option<PathBuf>, Option<Vec<OsString>>);

fn walked_entry_row(entry: crate::snapshot::models::WalkedEntry) -> WalkedEntryRow {
    (
        entry.entry_path,
        entry.canonical_path,
        entry.root_relative_parts,
    )
}

#[pyfunction]
pub(crate) fn walk_python_files(py: Python<'_>, roots: Vec<PathBuf>) -> Vec<Vec<WalkedEntryRow>> {
    let walked = py.detach(move || snapshot_walk(&roots));
    walked
        .into_iter()
        .map(|entries| entries.into_iter().map(walked_entry_row).collect())
        .collect()
}

#[pyfunction]
pub(crate) fn hash_source_files(py: Python<'_>, paths: Vec<PathBuf>) -> Vec<Option<String>> {
    py.detach(move || hash_files(&paths))
}
