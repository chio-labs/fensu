//! Python-callable bindings over memory engine entries.

use std::path::PathBuf;

use pyo3::exceptions::PyRuntimeError;
use pyo3::types::PyTuple;
use pyo3::{pyfunction, Py, PyErr, PyResult, Python};

use crate::extension::helpers::memory_conversion;
use fensu_memory::engine::errors::MemoryIndexError;
use fensu_memory::engine::main::archive_memory::archive_memory;
use fensu_memory::engine::main::check_memory::check_memory;
use fensu_memory::engine::main::memory_overview::memory_overview as overview;
use fensu_memory::engine::main::memory_relation_schema::memory_relation_schema as relation_schema;
use fensu_memory::engine::main::memory_schema as schema_metadata;
use fensu_memory::engine::main::memory_schema_sql as schema;
use fensu_memory::engine::main::probe_dependencies::probe_dependencies;
use fensu_memory::engine::main::query_memory_graph::query_memory_graph;
use fensu_memory::engine::main::query_memory_index::query_memory_index;
use fensu_memory::engine::main::rebuild_memory_index::rebuild_memory_index;
use fensu_memory::engine::main::summarize_memory::summarize_memory;
use fensu_memory::engine::main::sync_memory_index::sync_memory_index;
use fensu_memory::engine::models::{
    MemoryGraphDirection, MemoryGraphQuery, MemoryGraphRelationship,
};

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
pub(crate) fn memory_archive(
    py: Python<'_>,
    repository_root: PathBuf,
    database_path: PathBuf,
    requested_paths: Vec<PathBuf>,
    archive_after_days: u64,
    confirmed: bool,
) -> PyResult<Py<PyTuple>> {
    let result = py
        .detach(move || {
            archive_memory(
                &repository_root,
                &database_path,
                &requested_paths,
                archive_after_days,
                confirmed,
            )
        })
        .map_err(memory_index_error)?;
    memory_conversion::memory_archive_result_object(py, result)
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

#[pyfunction]
pub(crate) fn memory_graph(
    py: Python<'_>,
    database_path: PathBuf,
    request: (String, String, Vec<String>, usize, usize, usize, bool),
) -> PyResult<Py<PyTuple>> {
    let (pattern, direction, relationships, depth, max_nodes, max_edges, include_archived) =
        request;
    let query = MemoryGraphQuery {
        pattern,
        direction: graph_direction(&direction).map_err(memory_index_error)?,
        relationships: relationships
            .iter()
            .map(|value| graph_relationship(value))
            .collect::<Result<Vec<MemoryGraphRelationship>, MemoryIndexError>>()
            .map_err(memory_index_error)?,
        depth,
        max_nodes,
        max_edges,
        include_archived,
    };
    let result = py
        .detach(move || query_memory_graph(&database_path, &query))
        .map_err(memory_index_error)?;
    memory_conversion::memory_graph_result_object(py, result)
}

fn graph_direction(value: &str) -> Result<MemoryGraphDirection, MemoryIndexError> {
    match value {
        "outbound" => Ok(MemoryGraphDirection::Outbound),
        "inbound" => Ok(MemoryGraphDirection::Inbound),
        "both" => Ok(MemoryGraphDirection::Both),
        _ => Err(MemoryIndexError::GraphQuery(format!(
            "unsupported direction: {value}"
        ))),
    }
}

fn graph_relationship(value: &str) -> Result<MemoryGraphRelationship, MemoryIndexError> {
    match value {
        "link" => Ok(MemoryGraphRelationship::Link),
        "related" => Ok(MemoryGraphRelationship::Related),
        "depends-on" => Ok(MemoryGraphRelationship::DependsOn),
        "supersedes" => Ok(MemoryGraphRelationship::Supersedes),
        "discovered-from" => Ok(MemoryGraphRelationship::DiscoveredFrom),
        "implements" => Ok(MemoryGraphRelationship::Implements),
        "documents" => Ok(MemoryGraphRelationship::Documents),
        _ => Err(MemoryIndexError::GraphQuery(format!(
            "unsupported relationship: {value}"
        ))),
    }
}

fn memory_index_error(error: MemoryIndexError) -> PyErr {
    PyRuntimeError::new_err(error.to_string())
}
