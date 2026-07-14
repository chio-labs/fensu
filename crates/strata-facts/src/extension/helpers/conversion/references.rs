//! Convert reference and test module-shape rows into Python facts.

use pyo3::types::{PyAnyMethods, PyTuple};
use pyo3::{Bound, Py, PyAny, PyResult, Python};

use crate::constants;
use crate::extension::helpers::conversion::annotations::location_object;
use crate::extension::helpers::conversion::declarations::{location_tuple, to_object};
use crate::extension::helpers::gateway::model_types::model_type;
use crate::extension::helpers::gateway::program::ProgramHandle;
use crate::facts::main::extract_references::extract_references;
use crate::facts::main::extract_test_module::extract_test_module;
use crate::facts::models::{ImportRow, ReferenceEventRow};

pub(crate) fn reference_facts_object(
    py: Python<'_>,
    program: &ProgramHandle,
    path: &Bound<'_, PyAny>,
) -> PyResult<Py<PyAny>> {
    let rows = extract_references(program.module(), program.index(), program.source());
    let mut import_objects: Vec<Py<PyAny>> = Vec::with_capacity(rows.imports.len());
    for row in &rows.imports {
        import_objects.push(import_fact_object(py, path, row)?);
    }
    let attribute_constructor = model_type(py, constants::ATTRIBUTE_REFERENCE_FACT_NAME)?;
    let mut event_objects: Vec<Py<PyAny>> = Vec::with_capacity(rows.events.len());
    for event in &rows.events {
        match event {
            ReferenceEventRow::Import(slot) => {
                if let Some(fact) = import_objects.get(*slot) {
                    event_objects.push(fact.clone_ref(py));
                }
            }
            ReferenceEventRow::Attribute {
                line,
                column,
                base_name,
                attribute_name,
            } => {
                let location = location_object(py, path, *line, *column)?;
                event_objects.push(
                    attribute_constructor
                        .call1((location, base_name.as_deref(), attribute_name))?
                        .unbind(),
                );
            }
        }
    }
    let constructor = model_type(py, constants::REFERENCE_FACTS_NAME)?;
    let imports_tuple = PyTuple::new(py, import_objects)?;
    let events_tuple = PyTuple::new(py, event_objects)?;
    Ok(constructor.call1((imports_tuple, events_tuple))?.unbind())
}

fn import_fact_object(
    py: Python<'_>,
    path: &Bound<'_, PyAny>,
    row: &ImportRow,
) -> PyResult<Py<PyAny>> {
    let alias_constructor = model_type(py, constants::IMPORT_ALIAS_FACT_NAME)?;
    let mut alias_objects: Vec<Py<PyAny>> = Vec::with_capacity(row.aliases.len());
    for alias in &row.aliases {
        let imported_parts: Vec<&str> = alias
            .imported_name
            .split(constants::MODULE_SEPARATOR)
            .collect();
        let parts_tuple = PyTuple::new(py, imported_parts)?;
        alias_objects.push(
            alias_constructor
                .call1((&alias.imported_name, parts_tuple, &alias.bound_name))?
                .unbind(),
        );
    }
    let module_parts = PyTuple::new(py, &row.module_parts)?;
    let aliases_tuple = PyTuple::new(py, alias_objects)?;
    let constructor = model_type(py, constants::IMPORT_FACT_NAME)?;
    let arguments = PyTuple::new(
        py,
        vec![
            location_object(py, path, row.line, row.column)?.unbind(),
            module_parts.into_any().unbind(),
            aliases_tuple.into_any().unbind(),
            to_object(py, row.relative_level)?,
            to_object(py, row.from_import)?,
            to_object(py, row.top_level)?,
        ],
    )?;
    Ok(constructor.call1(arguments)?.unbind())
}

pub(crate) fn test_module_facts_object(
    py: Python<'_>,
    program: &ProgramHandle,
    path: &Bound<'_, PyAny>,
) -> PyResult<Py<PyAny>> {
    let rows = extract_test_module(program.module(), program.index(), program.source());
    let constructor = model_type(py, constants::PYTEST_MODULE_FACTS_NAME)?;
    let arguments = PyTuple::new(
        py,
        vec![
            to_object(py, rows.empty_or_docstring_only)?,
            location_tuple(py, path, &rows.scenario_invalid)?,
            location_tuple(py, path, &rows.top_level_helpers)?,
            location_tuple(py, path, &rows.test_case_lists)?,
            location_tuple(py, path, &rows.private_after_test)?,
        ],
    )?;
    Ok(constructor.call1(arguments)?.unbind())
}
