//! Python-callable bindings over native domain entries.

use pyo3::exceptions::PyValueError;
use pyo3::types::{PyAnyMethods, PyTuple};
use pyo3::{pyfunction, Bound, Py, PyAny, PyResult, Python};
use rayon::iter::{IntoParallelRefIterator, ParallelIterator};
use ruff_python_ast::PythonVersion;

use crate::constants;
use crate::extension::helpers::conversion::annotations::annotation_facts_object;
use crate::extension::helpers::conversion::contracts::function_contract_facts_object;
use crate::extension::helpers::conversion::declarations::module_declaration_facts_object;
use crate::extension::helpers::conversion::functions::{
    dataclass_facts_object, function_facts_object, parameter_mutation_facts_object,
    project_facts_objects,
};
use crate::extension::helpers::conversion::harness::{
    evaluate_rule_call_facts_object, test_function_facts_object,
};
use crate::extension::helpers::conversion::hygiene::{
    control_flow_facts_objects, hygiene_facts_object,
};
use crate::extension::helpers::conversion::mapping::mapping_rows_object;
use crate::extension::helpers::conversion::references::{
    reference_facts_object, test_module_facts_object,
};
use crate::extension::helpers::conversion::state::outer_state_mutation_facts_object;
use crate::extension::helpers::gateway::model_types::model_type;
use crate::extension::models::ProgramHandle;
use crate::facts::main::enumerate_nodes::enumerate_nodes;
use crate::facts::mapping::main::extract_mapping_declarations::extract_mapping_declarations;
use crate::facts::mapping::main::extract_mapping_facts::extract_mapping_facts;
use crate::facts::types::FactFamily;
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
pub(crate) fn parse_programs(
    py: Python<'_>,
    sources: Vec<String>,
    major: u8,
    minor: u8,
) -> Vec<Option<ProgramHandle>> {
    let version = PythonVersion { major, minor };
    py.detach(move || ProgramHandle::parse_many(sources, version))
}

#[pyfunction]
pub(crate) fn mapping_index_facts(
    py: Python<'_>,
    handle: &Bound<'_, ProgramHandle>,
) -> PyResult<Py<PyAny>> {
    let program = handle.get();
    let rows =
        py.detach(|| extract_mapping_facts(program.module(), program.index(), program.source()));
    mapping_rows_object(py, &rows)
}

#[pyfunction]
pub(crate) fn mapping_declaration_facts(
    py: Python<'_>,
    handle: &Bound<'_, ProgramHandle>,
) -> PyResult<Py<PyAny>> {
    let program = handle.get();
    let rows = py.detach(|| {
        extract_mapping_declarations(program.module(), program.index(), program.source())
    });
    mapping_rows_object(py, &rows)
}

#[pyfunction]
pub(crate) fn extract_fact_rows(
    py: Python<'_>,
    requests: Vec<(Py<ProgramHandle>, Vec<String>)>,
) -> usize {
    let prepared: Vec<(Py<ProgramHandle>, Vec<FactFamily>)> = requests
        .into_iter()
        .map(|(handle, names)| {
            let families: Vec<FactFamily> =
                names.iter().filter_map(|name| fact_family(name)).collect();
            (handle, families)
        })
        .collect();
    py.detach(move || {
        prepared
            .par_iter()
            .map(|(handle, families)| {
                let program = handle.get();
                for family in families {
                    program.extract_rows(*family);
                }
                families.len()
            })
            .sum()
    })
}

fn fact_family(name: &str) -> Option<FactFamily> {
    match name {
        "annotations" => Some(FactFamily::Annotations),
        "assignment_references" => Some(FactFamily::AssignmentReferences),
        "class_declarations" => Some(FactFamily::ClassDeclarations),
        "comments" => Some(FactFamily::Comments),
        "comparisons" => Some(FactFamily::Comparisons),
        "contracts" => Some(FactFamily::Contracts),
        "control_flow" => Some(FactFamily::ControlFlow),
        "dataclasses" => Some(FactFamily::Dataclasses),
        "declarations" => Some(FactFamily::Declarations),
        "functions" => Some(FactFamily::Functions),
        "hygiene" => Some(FactFamily::Hygiene),
        "local_call_edges" => Some(FactFamily::LocalCallEdges),
        "named_calls" => Some(FactFamily::NamedCalls),
        "outer_state_mutations" => Some(FactFamily::OuterStateMutations),
        "parameter_mutations" => Some(FactFamily::ParameterMutations),
        "parameter_mutation_occurrences" => Some(FactFamily::ParameterMutationOccurrences),
        "references" => Some(FactFamily::References),
        "test_functions" => Some(FactFamily::TestFunctions),
        "test_module" => Some(FactFamily::TestModule),
        _ => None,
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
pub(crate) fn evaluate_rule_call_facts(
    py: Python<'_>,
    handle: &Bound<'_, ProgramHandle>,
    path: &Bound<'_, PyAny>,
) -> PyResult<Py<PyAny>> {
    evaluate_rule_call_facts_object(py, handle.get(), path)
}

#[pyfunction]
pub(crate) fn test_function_facts(
    py: Python<'_>,
    handle: &Bound<'_, ProgramHandle>,
    path: &Bound<'_, PyAny>,
) -> PyResult<Py<PyAny>> {
    test_function_facts_object(py, handle.get(), path)
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
    let rows = program.comment_rows();
    let constructor = model_type(py, constants::COMMENT_FACT_NAME)?;
    let mut facts: Vec<Py<PyAny>> = Vec::with_capacity(rows.len());
    for row in rows {
        let fact = constructor.call1((path, row.line, row.column, &row.text))?;
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
