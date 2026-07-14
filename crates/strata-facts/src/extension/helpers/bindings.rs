//! Python-callable bindings over native domain entries.

use pyo3::exceptions::PyValueError;
use pyo3::types::{PyAnyMethods, PyTuple};
use pyo3::{pyfunction, Bound, Py, PyAny, PyResult, Python};
use ruff_python_ast::PythonVersion;

use crate::constants;
use crate::extension::helpers::convert_annotations::annotation_facts_object;
use crate::extension::helpers::convert_contracts::function_contract_facts_object;
use crate::extension::helpers::convert_declarations::module_declaration_facts_object;
use crate::extension::helpers::convert_functions::{
    dataclass_facts_object, function_facts_object, parameter_mutation_facts_object,
    project_facts_objects,
};
use crate::extension::helpers::convert_hygiene::{
    control_flow_facts_objects, hygiene_facts_object,
};
use crate::extension::helpers::convert_references::{
    reference_facts_object, test_module_facts_object,
};
use crate::extension::helpers::convert_state::outer_state_mutation_facts_object;
use crate::extension::helpers::model_types::model_type;
use crate::extension::helpers::program::ProgramHandle;
use crate::facts::main::enumerate_nodes::enumerate_nodes;
use crate::facts::main::extract_comments::extract_comments;
use crate::parsing::main::parse_strict::parse_strict;
use crate::positions::main::locate_offset::locate_offset;

#[pyfunction]
pub(crate) fn backend_version() -> String {
    env!("CARGO_PKG_VERSION").to_owned()
}

#[pyfunction]
pub(crate) fn locate_byte_offset(source: &str, offset: usize) -> (u32, u32) {
    let location = locate_offset(source, offset);
    (location.line, location.column)
}

type SyntaxNodeRows = Vec<(String, Option<(u32, u32, u32, u32)>)>;

#[pyfunction]
pub(crate) fn list_syntax_nodes(source: &str, major: u8, minor: u8) -> PyResult<SyntaxNodeRows> {
    let version = PythonVersion { major, minor };
    match enumerate_nodes(source, version) {
        Ok(nodes) => Ok(nodes
            .into_iter()
            .map(|node| (node.kind.to_owned(), node.span))
            .collect()),
        Err(failure) => Err(PyValueError::new_err(failure.message)),
    }
}

#[pyfunction]
pub(crate) fn parse_program(source: &str, major: u8, minor: u8) -> PyResult<ProgramHandle> {
    let version = PythonVersion { major, minor };
    match ProgramHandle::parse(source, version) {
        Ok(handle) => Ok(handle),
        Err(failure) => Err(PyValueError::new_err(failure.message)),
    }
}

#[pyfunction]
pub(crate) fn annotation_facts(
    py: Python<'_>,
    handle: &Bound<'_, ProgramHandle>,
    path: &Bound<'_, PyAny>,
) -> PyResult<Py<PyAny>> {
    annotation_facts_object(py, handle.get(), path)
}

#[pyfunction]
pub(crate) fn function_contract_facts(
    py: Python<'_>,
    handle: &Bound<'_, ProgramHandle>,
    path: &Bound<'_, PyAny>,
) -> PyResult<Option<Py<PyAny>>> {
    function_contract_facts_object(py, handle.get(), path)
}

#[pyfunction]
pub(crate) fn function_facts(
    py: Python<'_>,
    handle: &Bound<'_, ProgramHandle>,
    path: &Bound<'_, PyAny>,
) -> PyResult<Py<PyAny>> {
    function_facts_object(py, handle.get(), path)
}

#[pyfunction]
pub(crate) fn parameter_mutation_facts(
    py: Python<'_>,
    handle: &Bound<'_, ProgramHandle>,
    path: &Bound<'_, PyAny>,
) -> PyResult<Py<PyAny>> {
    parameter_mutation_facts_object(py, handle.get(), path)
}

#[pyfunction]
pub(crate) fn outer_state_mutation_facts(
    py: Python<'_>,
    handle: &Bound<'_, ProgramHandle>,
    path: &Bound<'_, PyAny>,
) -> PyResult<Py<PyAny>> {
    outer_state_mutation_facts_object(py, handle.get(), path)
}

#[pyfunction]
pub(crate) fn reference_facts(
    py: Python<'_>,
    handle: &Bound<'_, ProgramHandle>,
    path: &Bound<'_, PyAny>,
) -> PyResult<Py<PyAny>> {
    reference_facts_object(py, handle.get(), path)
}

#[pyfunction]
pub(crate) fn test_module_facts(
    py: Python<'_>,
    handle: &Bound<'_, ProgramHandle>,
    path: &Bound<'_, PyAny>,
) -> PyResult<Py<PyAny>> {
    test_module_facts_object(py, handle.get(), path)
}

#[pyfunction]
pub(crate) fn hygiene_facts(
    py: Python<'_>,
    handle: &Bound<'_, ProgramHandle>,
    path: &Bound<'_, PyAny>,
) -> PyResult<Py<PyAny>> {
    hygiene_facts_object(py, handle.get(), path)
}

#[pyfunction]
pub(crate) fn control_flow_facts(
    py: Python<'_>,
    handle: &Bound<'_, ProgramHandle>,
    path: &Bound<'_, PyAny>,
) -> PyResult<(Py<PyAny>, Py<PyAny>, Py<PyAny>)> {
    control_flow_facts_objects(py, handle.get(), path)
}

#[pyfunction]
pub(crate) fn dataclass_facts(
    py: Python<'_>,
    handle: &Bound<'_, ProgramHandle>,
    path: &Bound<'_, PyAny>,
) -> PyResult<Py<PyAny>> {
    dataclass_facts_object(py, handle.get(), path)
}

#[pyfunction]
pub(crate) fn project_facts(
    py: Python<'_>,
    handle: &Bound<'_, ProgramHandle>,
    path: &Bound<'_, PyAny>,
) -> PyResult<(Py<PyAny>, Py<PyAny>)> {
    project_facts_objects(py, handle.get(), path)
}

#[pyfunction]
pub(crate) fn module_declaration_facts(
    py: Python<'_>,
    handle: &Bound<'_, ProgramHandle>,
    path: &Bound<'_, PyAny>,
) -> PyResult<Py<PyAny>> {
    module_declaration_facts_object(py, handle.get(), path)
}

#[pyfunction]
pub(crate) fn comment_facts(
    py: Python<'_>,
    handle: &Bound<'_, ProgramHandle>,
    path: &Bound<'_, PyAny>,
) -> PyResult<Py<PyTuple>> {
    let program = handle.get();
    let rows = extract_comments(program.tokens(), program.source(), program.index());
    let constructor = model_type(py, constants::COMMENT_FACT_NAME)?;
    let mut facts: Vec<Py<PyAny>> = Vec::with_capacity(rows.len());
    for row in rows {
        let fact = constructor.call1((path, row.line, row.column, row.text))?;
        facts.push(fact.unbind());
    }
    Ok(PyTuple::new(py, facts)?.unbind())
}

#[pyfunction]
pub(crate) fn check_syntax(source: &str, major: u8, minor: u8) -> Option<(u32, u32, String)> {
    let version = PythonVersion { major, minor };
    match parse_strict(source, version) {
        Ok(_) => None,
        Err(failure) => Some((failure.line, failure.column, failure.message)),
    }
}
