//! Convert memory engine results into owned Python builtins.

use pyo3::types::{PyAnyMethods, PyDict, PyDictMethods, PyList, PyTuple};
use pyo3::{Bound, BoundObject, IntoPyObject, Py, PyAny, PyErr, PyResult, Python};

use fensu_memory::engine::models::{
    IndexSummary, MemoryArchiveResult, MemoryCheckResult, MemoryDiagnostic, MemoryGraphEdge,
    MemoryGraphNode, MemoryGraphResult, MemoryOverview, MemoryQueryResult, MemoryQueryValue,
    MemorySchemaOverview, MemorySchemaRelation, MemorySummary, SyncSummary,
};

pub(crate) fn memory_summary_object(
    py: Python<'_>,
    summary: MemorySummary,
) -> PyResult<Py<PyTuple>> {
    PyTuple::new(
        py,
        [
            summary.document_count,
            summary.section_count,
            summary.list_item_count,
            summary.link_count,
            summary.tag_count,
            summary.skill_file_count,
            summary.source_diagnostic_count,
            summary.corpus_diagnostic_count,
            summary.graph_diagnostic_count,
        ],
    )
    .map(Bound::unbind)
}

pub(crate) fn index_summary_object(py: Python<'_>, summary: IndexSummary) -> PyResult<Py<PyTuple>> {
    PyTuple::new(
        py,
        [
            summary.document_count,
            summary.section_count,
            summary.list_item_count,
            summary.link_count,
            summary.tag_count,
            summary.skill_file_count,
            summary.source_diagnostic_count,
            summary.corpus_diagnostic_count,
            summary.graph_diagnostic_count,
        ],
    )
    .map(Bound::unbind)
}

pub(crate) fn sync_summary_object(py: Python<'_>, summary: SyncSummary) -> PyResult<Py<PyTuple>> {
    PyTuple::new(
        py,
        [
            to_object(py, summary.added_count)?,
            to_object(py, summary.changed_count)?,
            to_object(py, summary.moved_count)?,
            to_object(py, summary.removed_count)?,
            to_object(py, summary.unchanged_count)?,
            to_object(py, summary.rebuilt)?,
            to_object(py, summary.changed)?,
            to_object(py, summary.document_count)?,
            to_object(py, summary.section_count)?,
            to_object(py, summary.link_count)?,
        ],
    )
    .map(Bound::unbind)
}

pub(crate) fn memory_overview_object(
    py: Python<'_>,
    overview: MemoryOverview,
) -> PyResult<Py<PyTuple>> {
    PyTuple::new(
        py,
        [
            overview.not_started_task_count,
            overview.in_progress_task_count,
            overview.completed_task_count,
            overview.cancelled_task_count,
            overview.superseded_task_count,
            overview.active_note_count,
            overview.active_decision_count,
            overview.active_skill_count,
            overview.archived_task_count,
            overview.archived_knowledge_count,
            overview.document_count,
            overview.section_count,
        ],
    )
    .map(Bound::unbind)
}

pub(crate) fn memory_schema_object(
    py: Python<'_>,
    schema: MemorySchemaOverview,
) -> PyResult<Py<PyTuple>> {
    let relations = schema
        .relations
        .into_iter()
        .map(|relation| {
            PyTuple::new(py, [relation.name, relation.kind, relation.comment]).map(Bound::unbind)
        })
        .collect::<PyResult<Vec<Py<PyTuple>>>>()?;
    PyTuple::new(
        py,
        [
            to_object(py, schema.schema_version)?,
            to_object(py, schema.parser_contract_version)?,
            PyTuple::new(py, relations)?.into_any().unbind(),
        ],
    )
    .map(Bound::unbind)
}

pub(crate) fn memory_relation_schema_object(
    py: Python<'_>,
    relation: MemorySchemaRelation,
) -> PyResult<Py<PyTuple>> {
    let columns = relation
        .columns
        .iter()
        .map(|column| {
            PyTuple::new(
                py,
                [
                    to_object(py, column.name)?,
                    to_object(py, column.data_type)?,
                    to_object(py, column.nullable)?,
                    to_object(py, column.comment)?,
                ],
            )
            .map(Bound::unbind)
        })
        .collect::<PyResult<Vec<Py<PyTuple>>>>()?;
    PyTuple::new(
        py,
        [
            to_object(py, relation.name)?,
            to_object(py, relation.kind)?,
            to_object(py, relation.comment)?,
            PyTuple::new(py, columns)?.into_any().unbind(),
        ],
    )
    .map(Bound::unbind)
}

pub(crate) fn memory_check_result_object(
    py: Python<'_>,
    result: MemoryCheckResult,
) -> PyResult<Py<PyTuple>> {
    let diagnostics = result
        .diagnostics
        .into_iter()
        .map(|diagnostic| memory_diagnostic_object(py, diagnostic))
        .collect::<PyResult<Vec<Py<PyTuple>>>>()?;
    let published = match result.published {
        Some(summary) => index_summary_object(py, summary)?.into_any(),
        None => py.None(),
    };
    PyTuple::new(
        py,
        [
            PyTuple::new(py, diagnostics)?.into_any().unbind(),
            published,
        ],
    )
    .map(Bound::unbind)
}

pub(crate) fn memory_archive_result_object(
    py: Python<'_>,
    result: MemoryArchiveResult,
) -> PyResult<Py<PyTuple>> {
    let moves = result
        .moves
        .into_iter()
        .map(|entry| PyTuple::new(py, [entry.source, entry.destination]).map(Bound::unbind))
        .collect::<PyResult<Vec<Py<PyTuple>>>>()?;
    let sync = match result.sync {
        Some(summary) => sync_summary_object(py, summary)?.into_any(),
        None => py.None(),
    };
    PyTuple::new(py, [PyTuple::new(py, moves)?.into_any().unbind(), sync]).map(Bound::unbind)
}

pub(crate) fn memory_query_result_object(
    py: Python<'_>,
    result: MemoryQueryResult,
) -> PyResult<Py<PyTuple>> {
    let integer_constructor = py.import("builtins")?.getattr("int")?;
    let columns = PyTuple::new(py, result.columns)?.into_any().unbind();
    let types = PyTuple::new(py, result.types)?.into_any().unbind();
    let rows = query_rows_object(py, result.rows, &integer_constructor)?;
    let truncated = to_object(py, result.truncated)?;
    PyTuple::new(py, [columns, types, rows, truncated]).map(Bound::unbind)
}

pub(crate) fn memory_graph_result_object(
    py: Python<'_>,
    result: MemoryGraphResult,
) -> PyResult<Py<PyTuple>> {
    let roots = PyTuple::new(py, result.roots)?.into_any().unbind();
    let nodes = result
        .nodes
        .into_iter()
        .map(|node| memory_graph_node_object(py, node))
        .collect::<PyResult<Vec<Py<PyTuple>>>>()?;
    let edges = result
        .edges
        .into_iter()
        .map(|edge| memory_graph_edge_object(py, edge))
        .collect::<PyResult<Vec<Py<PyTuple>>>>()?;
    PyTuple::new(
        py,
        [
            to_object(py, result.selection)?,
            roots,
            PyTuple::new(py, nodes)?.into_any().unbind(),
            PyTuple::new(py, edges)?.into_any().unbind(),
            to_object(py, result.node_budget_exhausted)?,
            to_object(py, result.edge_budget_exhausted)?,
        ],
    )
    .map(Bound::unbind)
}

fn memory_graph_node_object(py: Python<'_>, node: MemoryGraphNode) -> PyResult<Py<PyTuple>> {
    PyTuple::new(
        py,
        [
            to_object(py, node.identity)?,
            to_object(py, node.artifact_kind)?,
            to_object(py, node.archive_state)?,
            to_object(py, node.repository_relative_path)?,
            to_object(py, node.basename)?,
            to_object(py, node.slug)?,
            to_object(py, node.title)?,
            to_object(py, node.depth)?,
            to_object(py, node.root)?,
        ],
    )
    .map(Bound::unbind)
}

fn memory_graph_edge_object(py: Python<'_>, edge: MemoryGraphEdge) -> PyResult<Py<PyTuple>> {
    PyTuple::new(
        py,
        [
            to_object(py, edge.source_document_identity)?,
            to_object(py, edge.source_link_ordinal)?,
            to_object(py, edge.relationship)?,
            to_object(py, edge.authored_target)?,
            to_object(py, edge.resolution_status)?,
            to_object(py, edge.target_document_identity)?,
            to_object(py, edge.cycle)?,
        ],
    )
    .map(Bound::unbind)
}

fn query_rows_object(
    py: Python<'_>,
    rows: Vec<Vec<MemoryQueryValue>>,
    integer_constructor: &Bound<'_, PyAny>,
) -> PyResult<Py<PyAny>> {
    let mut objects: Vec<Py<PyTuple>> = Vec::with_capacity(rows.len());
    for row in rows {
        let mut values: Vec<Py<PyAny>> = Vec::with_capacity(row.len());
        for value in row {
            values.push(query_value_object(py, value, integer_constructor)?);
        }
        objects.push(PyTuple::new(py, values)?.unbind());
    }
    Ok(PyTuple::new(py, objects)?.into_any().unbind())
}

fn memory_diagnostic_object(py: Python<'_>, diagnostic: MemoryDiagnostic) -> PyResult<Py<PyTuple>> {
    PyTuple::new(
        py,
        [
            to_object(py, diagnostic.code)?,
            to_object(py, diagnostic.repository_relative_path)?,
            to_object(py, diagnostic.line)?,
            to_object(py, diagnostic.column)?,
            to_object(py, diagnostic.message)?,
            to_object(py, diagnostic.remediation)?,
        ],
    )
    .map(Bound::unbind)
}

fn query_value_object(
    py: Python<'_>,
    value: MemoryQueryValue,
    integer_constructor: &Bound<'_, PyAny>,
) -> PyResult<Py<PyAny>> {
    match value {
        MemoryQueryValue::Null => Ok(py.None()),
        MemoryQueryValue::Boolean(value) => to_object(py, value),
        MemoryQueryValue::Integer(value) => Ok(integer_constructor.call1((value,))?.unbind()),
        MemoryQueryValue::Float(value) => to_object(py, value),
        MemoryQueryValue::String(value) => to_object(py, value),
        MemoryQueryValue::Array(values) => array_object(py, values, integer_constructor),
        MemoryQueryValue::Object(fields) => object_value(py, fields, integer_constructor),
    }
}

fn array_object(
    py: Python<'_>,
    values: Vec<MemoryQueryValue>,
    integer_constructor: &Bound<'_, PyAny>,
) -> PyResult<Py<PyAny>> {
    let mut objects: Vec<Py<PyAny>> = Vec::with_capacity(values.len());
    for value in values {
        objects.push(query_value_object(py, value, integer_constructor)?);
    }
    Ok(PyList::new(py, objects)?.into_any().unbind())
}

fn object_value(
    py: Python<'_>,
    fields: Vec<(String, MemoryQueryValue)>,
    integer_constructor: &Bound<'_, PyAny>,
) -> PyResult<Py<PyAny>> {
    let object = PyDict::new(py);
    for (key, value) in fields {
        object.set_item(key, query_value_object(py, value, integer_constructor)?)?;
    }
    Ok(object.into_any().unbind())
}

fn to_object<'py, T>(py: Python<'py>, value: T) -> PyResult<Py<PyAny>>
where
    T: IntoPyObject<'py>,
    PyErr: From<T::Error>,
{
    Ok(value.into_pyobject(py)?.into_any().unbind())
}

#[cfg(test)]
#[path = "../../../tests/extension/test_types.rs"]
mod test_types;
#[cfg(test)]
#[path = "../../../tests/extension/memory_conversion.rs"]
mod tests;
