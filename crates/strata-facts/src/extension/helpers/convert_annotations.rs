//! Convert annotation rows into Python fact model instances.

use pyo3::types::{PyAnyMethods, PyTuple};
use pyo3::{Bound, Py, PyAny, PyResult, Python};

use crate::constants;
use crate::extension::helpers::model_types::model_type;
use crate::extension::helpers::program::ProgramHandle;
use crate::facts::main::extract_annotations::extract_annotations;
use crate::facts::models::{LocalAnnotationRow, NamedLocationRow};

pub(crate) fn annotation_facts_object(
    py: Python<'_>,
    program: &ProgramHandle,
    path: &Bound<'_, PyAny>,
) -> PyResult<Py<PyAny>> {
    let rows = extract_annotations(program.module(), program.index(), program.source());
    let parameters = named_facts(
        py,
        path,
        constants::MISSING_PARAMETER_ANNOTATION_NAME,
        &rows.parameters,
    )?;
    let returns = named_facts(
        py,
        path,
        constants::MISSING_RETURN_ANNOTATION_NAME,
        &rows.returns,
    )?;
    let locals = local_facts(py, path, &rows.locals)?;
    let module_variables = named_facts(
        py,
        path,
        constants::MISSING_VARIABLE_ANNOTATION_NAME,
        &rows.module_variables,
    )?;
    let class_attributes = named_facts(
        py,
        path,
        constants::MISSING_VARIABLE_ANNOTATION_NAME,
        &rows.class_attributes,
    )?;
    let constructor = model_type(py, constants::ANNOTATION_FACTS_NAME)?;
    let facts = constructor.call1((
        parameters,
        returns,
        locals,
        module_variables,
        class_attributes,
    ))?;
    Ok(facts.unbind())
}

pub(crate) fn location_object<'py>(
    py: Python<'py>,
    path: &Bound<'py, PyAny>,
    line: u32,
    column: u32,
) -> PyResult<Bound<'py, PyAny>> {
    model_type(py, constants::SOURCE_LOCATION_NAME)?.call1((path, line, column))
}

fn named_facts(
    py: Python<'_>,
    path: &Bound<'_, PyAny>,
    type_name: &str,
    rows: &[NamedLocationRow],
) -> PyResult<Py<PyTuple>> {
    let constructor = model_type(py, type_name)?;
    let mut facts: Vec<Py<PyAny>> = Vec::with_capacity(rows.len());
    for row in rows {
        let location = location_object(py, path, row.line, row.column)?;
        facts.push(constructor.call1((&row.name, location))?.unbind());
    }
    Ok(PyTuple::new(py, facts)?.unbind())
}

fn local_facts(
    py: Python<'_>,
    path: &Bound<'_, PyAny>,
    rows: &[LocalAnnotationRow],
) -> PyResult<Py<PyTuple>> {
    let constructor = model_type(py, constants::MISSING_LOCAL_ANNOTATION_NAME)?;
    let mut facts: Vec<Py<PyAny>> = Vec::with_capacity(rows.len());
    for row in rows {
        let location = location_object(py, path, row.line, row.column)?;
        facts.push(
            constructor
                .call1((&row.name, location, row.scalar_literal))?
                .unbind(),
        );
    }
    Ok(PyTuple::new(py, facts)?.unbind())
}
