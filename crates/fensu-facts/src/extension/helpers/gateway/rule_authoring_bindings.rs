//! Python bindings for public rule-authoring fact families.

use pyo3::{pyfunction, Bound, Py, PyAny, PyResult, Python};

use crate::extension::helpers::conversion::rule_authoring::{
    assignment_reference_facts_object, class_declaration_facts_object, comparison_facts_object,
    local_call_edge_facts_object, named_call_facts_object,
    parameter_mutation_occurrence_facts_object,
};
use crate::extension::models::ProgramHandle;

#[pyfunction]
pub(crate) fn class_declaration_facts(
    py: Python<'_>,
    handle: &Bound<'_, ProgramHandle>,
    path: &Bound<'_, PyAny>,
) -> PyResult<Py<PyAny>> {
    class_declaration_facts_object(py, handle.get(), path)
}

#[pyfunction]
pub(crate) fn assignment_reference_facts(
    py: Python<'_>,
    handle: &Bound<'_, ProgramHandle>,
    path: &Bound<'_, PyAny>,
) -> PyResult<Py<PyAny>> {
    assignment_reference_facts_object(py, handle.get(), path)
}

#[pyfunction]
pub(crate) fn named_call_facts(
    py: Python<'_>,
    handle: &Bound<'_, ProgramHandle>,
    path: &Bound<'_, PyAny>,
) -> PyResult<Py<PyAny>> {
    named_call_facts_object(py, handle.get(), path)
}

#[pyfunction]
pub(crate) fn local_call_edge_facts(
    py: Python<'_>,
    handle: &Bound<'_, ProgramHandle>,
    path: &Bound<'_, PyAny>,
) -> PyResult<Py<PyAny>> {
    local_call_edge_facts_object(py, handle.get(), path)
}

#[pyfunction]
pub(crate) fn comparison_facts(
    py: Python<'_>,
    handle: &Bound<'_, ProgramHandle>,
    path: &Bound<'_, PyAny>,
) -> PyResult<Py<PyAny>> {
    comparison_facts_object(py, handle.get(), path)
}

#[pyfunction]
pub(crate) fn parameter_mutation_occurrence_facts(
    py: Python<'_>,
    handle: &Bound<'_, ProgramHandle>,
    path: &Bound<'_, PyAny>,
) -> PyResult<Py<PyAny>> {
    parameter_mutation_occurrence_facts_object(py, handle.get(), path)
}
