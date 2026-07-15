//! Python-callable bindings over native domain entries.

use std::ffi::OsString;
use std::path::PathBuf;

use pyo3::exceptions::PyValueError;
use pyo3::types::{PyAnyMethods, PyTuple};
use pyo3::{pyfunction, Bound, Py, PyAny, PyResult, Python};
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
use crate::extension::helpers::conversion::references::{
    reference_facts_object, test_module_facts_object,
};
use crate::extension::helpers::conversion::state::outer_state_mutation_facts_object;
use crate::extension::helpers::gateway::model_types::model_type;
use crate::extension::helpers::gateway::program::ProgramHandle;
use crate::facts::main::enumerate_nodes::enumerate_nodes;
use crate::facts::main::extract_comments::extract_comments;
use crate::parsing::main::parse_strict::parse_strict;
use crate::positions::main::locate_offset::locate_offset;
use crate::snapshot::main::hash_files::hash_files;
use crate::snapshot::main::observe_python_globs::observe_python_globs as observe_globs;
use crate::snapshot::main::observe_repository_contexts::observe_repository_contexts as observe_contexts;
use crate::snapshot::main::observe_repository_stats::observe_repository_stats as observe_stats;
use crate::snapshot::main::walk_python_files::walk_python_files as snapshot_walk;
use crate::snapshot::models::{
    RepositoryContextKind, RepositoryContextQuery, RepositoryPythonGlobQuery, RepositoryStatKind,
    RepositoryStatQuery,
};

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
