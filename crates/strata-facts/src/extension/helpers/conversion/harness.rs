//! Convert harness-use and test-function rows into Python facts.

use pyo3::types::{PyAnyMethods, PyFrozenSet, PyTuple};
use pyo3::{Bound, Py, PyAny, PyResult, Python};

use crate::constants;
use crate::extension::helpers::conversion::annotations::location_object;
use crate::extension::helpers::conversion::declarations::{location_tuple, to_object};
use crate::extension::helpers::gateway::model_types::{model_type, type_member};
use crate::extension::models::ProgramHandle;
use crate::facts::main::extract_evaluate_rule_calls::extract_evaluate_rule_calls;
use crate::facts::models::{DimensionRow, ParametrizeRow, StaticReferenceRow};

pub(crate) fn evaluate_rule_call_facts_object(
    py: Python<'_>,
    program: &ProgramHandle,
    path: &Bound<'_, PyAny>,
) -> PyResult<Py<PyAny>> {
    let rows = extract_evaluate_rule_calls(program.module(), program.index(), program.source());
    let constructor = model_type(py, constants::EVALUATE_RULE_CALL_FACT_NAME)?;
    let mut objects: Vec<Py<PyAny>> = Vec::with_capacity(rows.len());
    for row in rows {
        let arguments = PyTuple::new(
            py,
            vec![
                location_object(py, path, row.line, row.column)?.unbind(),
                to_object(py, row.test_function_name)?,
                optional_location(py, path, row.test_function_location)?,
                optional_name_tuple(py, row.rule_expression.as_deref())?,
                optional_location(py, path, row.rule_location)?,
                optional_reference(py, row.rule_reference.as_ref())?,
                optional_name_tuple(py, row.test_case_expression.as_deref())?,
                optional_location(py, path, row.test_case_location)?,
                type_member(py, constants::RULE_CASE_FORM_NAME, &row.test_case_form)?.unbind(),
                location_tuple(py, path, &row.case_locations)?,
                to_object(py, row.unknown_case_count)?,
            ],
        )?;
        objects.push(constructor.call1(arguments)?.unbind());
    }
    Ok(PyTuple::new(py, objects)?.into_any().unbind())
}

pub(crate) fn test_function_facts_object(
    py: Python<'_>,
    program: &ProgramHandle,
    path: &Bound<'_, PyAny>,
) -> PyResult<Py<PyAny>> {
    let rows = program.test_function_rows();
    let constructor = model_type(py, constants::PYTEST_FUNCTION_FACT_NAME)?;
    let mut objects: Vec<Py<PyAny>> = Vec::with_capacity(rows.len());
    for row in rows {
        let parameter_names = PyFrozenSet::new(py, &row.parameter_names)?;
        let parametrize = match &row.parametrize {
            Some(inner) => parametrize_object(py, path, inner)?,
            None => py.None(),
        };
        let arguments = PyTuple::new(
            py,
            vec![
                to_object(py, &row.name)?,
                location_object(py, path, row.line, row.column)?.unbind(),
                parameter_names.into_any().unbind(),
                to_object(py, row.test_case_annotation_name.as_deref())?,
                parametrize,
                to_object(py, row.references_expected_field)?,
                location_tuple(py, path, &row.conditional_locations)?,
                dimension_tuple(py, path, &row.dimensions)?,
            ],
        )?;
        objects.push(constructor.call1(arguments)?.unbind());
    }
    Ok(PyTuple::new(py, objects)?.into_any().unbind())
}

pub(crate) fn dimension_tuple(
    py: Python<'_>,
    path: &Bound<'_, PyAny>,
    rows: &[DimensionRow],
) -> PyResult<Py<PyAny>> {
    let constructor = model_type(py, constants::PARAMETRIZE_DIMENSION_FACT_NAME)?;
    let mut objects: Vec<Py<PyAny>> = Vec::with_capacity(rows.len());
    for row in rows {
        let parameter_names = PyTuple::new(py, &row.parameter_names)?;
        let arguments = PyTuple::new(
            py,
            vec![
                location_object(py, path, row.line, row.column)?.unbind(),
                parameter_names.into_any().unbind(),
                optional_location(py, path, row.values_location)?,
                location_tuple(py, path, &row.rule_case_locations)?,
                to_object(py, row.unknown_rule_case_count)?,
            ],
        )?;
        objects.push(constructor.call1(arguments)?.unbind());
    }
    Ok(PyTuple::new(py, objects)?.into_any().unbind())
}

fn parametrize_object(
    py: Python<'_>,
    path: &Bound<'_, PyAny>,
    row: &ParametrizeRow,
) -> PyResult<Py<PyAny>> {
    let case_constructor = model_type(py, constants::PARAMETRIZE_CASE_FACT_NAME)?;
    let mut cases: Vec<Py<PyAny>> = Vec::with_capacity(row.cases.len());
    for case in &row.cases {
        cases.push(
            case_constructor
                .call1((
                    location_object(py, path, case.line, case.column)?,
                    case.constructor_name.as_deref(),
                    case.dictionary,
                ))?
                .unbind(),
        );
    }
    let constructor = model_type(py, constants::PARAMETRIZE_FACT_NAME)?;
    let arguments = PyTuple::new(
        py,
        vec![
            to_object(py, row.argument_count)?,
            to_object(py, row.parameter_name.as_deref())?,
            to_object(py, row.ids_present)?,
            to_object(py, row.description_lambda_ids)?,
            to_object(py, row.values_is_comprehension)?,
            to_object(py, row.values_is_sequence)?,
            to_object(py, row.values_empty)?,
            PyTuple::new(py, cases)?.into_any().unbind(),
        ],
    )?;
    Ok(constructor.call1(arguments)?.unbind())
}

fn optional_location(
    py: Python<'_>,
    path: &Bound<'_, PyAny>,
    location: Option<(u32, u32)>,
) -> PyResult<Py<PyAny>> {
    match location {
        Some((line, column)) => Ok(location_object(py, path, line, column)?.unbind()),
        None => Ok(py.None()),
    }
}

fn optional_name_tuple(py: Python<'_>, names: Option<&[String]>) -> PyResult<Py<PyAny>> {
    match names {
        Some(inner) => Ok(PyTuple::new(py, inner)?.into_any().unbind()),
        None => Ok(py.None()),
    }
}

fn optional_reference(
    py: Python<'_>,
    reference: Option<&StaticReferenceRow>,
) -> PyResult<Py<PyAny>> {
    match reference {
        Some(inner) => Ok(model_type(py, constants::STATIC_REFERENCE_FACT_NAME)?
            .call1((&inner.module_name, &inner.symbol_name))?
            .unbind()),
        None => Ok(py.None()),
    }
}
