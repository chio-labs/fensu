//! Python-callable bindings over memory engine entries.

use std::path::PathBuf;

use pyo3::exceptions::PyRuntimeError;
use pyo3::types::PyTuple;
use pyo3::{pyfunction, Py, PyErr, PyResult, Python};

use crate::extension::helpers::memory_conversion;
use strata_memory::engine::errors::MemoryIndexError;
use strata_memory::engine::main::check_memory::check_memory;
use strata_memory::engine::main::memory_overview::memory_overview as overview;
use strata_memory::engine::main::memory_relation_schema::memory_relation_schema as relation_schema;
use strata_memory::engine::main::memory_schema as schema_metadata;
use strata_memory::engine::main::memory_schema_sql as schema;
use strata_memory::engine::main::probe_dependencies::probe_dependencies;
use strata_memory::engine::main::query_memory_index::query_memory_index;
use strata_memory::engine::main::rebuild_memory_index::rebuild_memory_index;
use strata_memory::engine::main::summarize_memory::summarize_memory;
use strata_memory::engine::main::sync_memory_index::sync_memory_index;

#[pyfunction]
pub(crate) fn memory_dependency_probe(
    py: Python<'_>,
    repository_root: PathBuf,
) -> PyResult<String> {
    py.detach(move || probe_dependencies(&repository_root))
        .map_err(PyRuntimeError::new_err)
}

#[pyfunction]
pub(crate) fn memory_summary(py: Python<'_>, repository_root: PathBuf) -> PyResult<Py<PyTuple>> {
    let summary = py.detach(move || summarize_memory(&repository_root));
    memory_conversion::memory_summary_object(py, summary)
}

#[pyfunction]
pub(crate) fn memory_rebuild(
    py: Python<'_>,
    repository_root: PathBuf,
    database_path: PathBuf,
) -> PyResult<Py<PyTuple>> {
    let summary = py
        .detach(move || rebuild_memory_index(&repository_root, &database_path))
        .map_err(memory_index_error)?;
    memory_conversion::index_summary_object(py, summary)
}

#[pyfunction]
pub(crate) fn memory_check(
    py: Python<'_>,
    repository_root: PathBuf,
    database_path: PathBuf,
) -> PyResult<Py<PyTuple>> {
    let result = py
        .detach(move || check_memory(&repository_root, &database_path))
        .map_err(memory_index_error)?;
    memory_conversion::memory_check_result_object(py, result)
}

#[pyfunction]
pub(crate) fn memory_sync(
    py: Python<'_>,
    repository_root: PathBuf,
    database_path: PathBuf,
) -> PyResult<Py<PyTuple>> {
    let summary = py
        .detach(move || sync_memory_index(&repository_root, &database_path))
        .map_err(memory_index_error)?;
    memory_conversion::sync_summary_object(py, summary)
}

#[pyfunction]
pub(crate) fn memory_overview(py: Python<'_>, database_path: PathBuf) -> PyResult<Py<PyTuple>> {
    let result = py
        .detach(move || overview(&database_path))
        .map_err(memory_index_error)?;
    memory_conversion::memory_overview_object(py, result)
}

#[pyfunction]
pub(crate) fn memory_schema_sql() -> &'static str {
    schema::memory_schema_sql()
}

#[pyfunction]
pub(crate) fn memory_schema(py: Python<'_>) -> PyResult<Py<PyTuple>> {
    memory_conversion::memory_schema_object(py, schema_metadata::memory_schema())
}

#[pyfunction]
pub(crate) fn memory_relation_schema(
    py: Python<'_>,
    name: String,
) -> PyResult<Option<Py<PyTuple>>> {
    relation_schema(&name)
        .map(|relation| memory_conversion::memory_relation_schema_object(py, relation))
        .transpose()
}

#[pyfunction]
pub(crate) fn memory_query(
    py: Python<'_>,
    database_path: PathBuf,
    sql: String,
    limit: usize,
) -> PyResult<Py<PyTuple>> {
    let result = py
        .detach(move || query_memory_index(&database_path, &sql, limit))
        .map_err(memory_index_error)?;
    memory_conversion::memory_query_result_object(py, result)
}

fn memory_index_error(error: MemoryIndexError) -> PyErr {
    PyRuntimeError::new_err(error.to_string())
}
