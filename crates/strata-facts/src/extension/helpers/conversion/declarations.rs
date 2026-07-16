//! Convert module-declaration rows into Python fact model instances.

use pyo3::types::{PyAnyMethods, PyFrozenSet, PyTuple};
use pyo3::{Bound, BoundObject, IntoPyObject, Py, PyAny, PyErr, PyResult, Python};

use crate::constants;
use crate::extension::helpers::conversion::annotations::location_object;
use crate::extension::helpers::gateway::model_types::model_type;
use crate::extension::helpers::gateway::program::ProgramHandle;
use crate::facts::models::{ModuleStatementRow, NamedCallRow, TypeDeclarationRow};

pub(crate) fn module_declaration_facts_object(
    py: Python<'_>,
    program: &ProgramHandle,
    path: &Bound<'_, PyAny>,
) -> PyResult<Py<PyAny>> {
    let rows = program.declaration_rows();
    let statements = statement_facts(py, path, &rows.statements)?;
    let constructor = model_type(py, constants::MODULE_DECLARATION_FACTS_NAME)?;
    let arguments = PyTuple::new(
        py,
        vec![
            statements,
            to_object(py, rows.empty_or_docstring_only)?,
            to_object(py, rows.pure_reexport)?,
            to_object(py, rows.top_level_class_count)?,
            location_tuple(py, path, &rows.all_assignment_locations)?,
            location_tuple(py, path, &rows.import_time_call_locations)?,
            frozen_names(py, &rows.imported_main_entry_names)?,
            named_call_facts(py, path, &rows.main_calls)?,
            location_tuple(py, path, &rows.model_locations)?,
            type_declaration_facts(py, path, &rows.type_declarations)?,
            location_tuple(py, path, &rows.exception_locations)?,
        ],
    )?;
    Ok(constructor.call1(arguments)?.unbind())
}

pub(crate) fn to_object<'py, T>(py: Python<'py>, value: T) -> PyResult<Py<PyAny>>
where
    T: IntoPyObject<'py>,
    PyErr: From<T::Error>,
{
    Ok(value.into_pyobject(py)?.into_any().unbind())
}

pub(crate) fn location_tuple(
    py: Python<'_>,
    path: &Bound<'_, PyAny>,
    locations: &[(u32, u32)],
) -> PyResult<Py<PyAny>> {
    let mut objects: Vec<Py<PyAny>> = Vec::with_capacity(locations.len());
    for (line, column) in locations {
        objects.push(location_object(py, path, *line, *column)?.unbind());
    }
    Ok(PyTuple::new(py, objects)?.into_any().unbind())
}

fn frozen_names(py: Python<'_>, names: &[String]) -> PyResult<Py<PyAny>> {
    Ok(PyFrozenSet::new(py, names)?.into_any().unbind())
}

fn named_call_facts(
    py: Python<'_>,
    path: &Bound<'_, PyAny>,
    rows: &[NamedCallRow],
) -> PyResult<Py<PyAny>> {
    let constructor = model_type(py, constants::NAMED_CALL_FACT_NAME)?;
    let mut objects: Vec<Py<PyAny>> = Vec::with_capacity(rows.len());
    for row in rows {
        let location = location_object(py, path, row.line, row.column)?;
        objects.push(constructor.call1((location, row.name.as_deref()))?.unbind());
    }
    Ok(PyTuple::new(py, objects)?.into_any().unbind())
}

fn type_declaration_facts(
    py: Python<'_>,
    path: &Bound<'_, PyAny>,
    rows: &[TypeDeclarationRow],
) -> PyResult<Py<PyAny>> {
    let constructor = model_type(py, constants::TYPE_DECLARATION_FACT_NAME)?;
    let mut objects: Vec<Py<PyAny>> = Vec::with_capacity(rows.len());
    for row in rows {
        let location = location_object(py, path, row.line, row.column)?;
        objects.push(constructor.call1((location, row.private))?.unbind());
    }
    Ok(PyTuple::new(py, objects)?.into_any().unbind())
}

fn statement_facts(
    py: Python<'_>,
    path: &Bound<'_, PyAny>,
    rows: &[ModuleStatementRow],
) -> PyResult<Py<PyAny>> {
    let constructor = model_type(py, constants::MODULE_STATEMENT_FACT_NAME)?;
    let mut objects: Vec<Py<PyAny>> = Vec::with_capacity(rows.len());
    for row in rows {
        let target_names = PyTuple::new(py, &row.assignment_target_names)?;
        let arguments = PyTuple::new(
            py,
            vec![
                location_object(py, path, row.line, row.column)?.unbind(),
                to_object(py, row.import_statement)?,
                to_object(py, row.assignment_statement)?,
                to_object(py, row.explicit_type_alias)?,
                to_object(py, row.type_checking_import_block)?,
                to_object(py, row.model_class)?,
                to_object(py, row.type_class)?,
                to_object(py, row.exception_class)?,
                target_names.into_any().unbind(),
                to_object(py, row.function_name.as_deref())?,
                to_object(py, row.class_name.as_deref())?,
                to_object(py, row.dataclass_class)?,
                to_object(py, row.docstring_statement)?,
                to_object(py, row.all_assignment)?,
                to_object(py, row.rule_decorated_function)?,
                to_object(py, row.nonexecuting_import_guard)?,
            ],
        )?;
        objects.push(constructor.call1(arguments)?.unbind());
    }
    Ok(PyTuple::new(py, objects)?.into_any().unbind())
}
