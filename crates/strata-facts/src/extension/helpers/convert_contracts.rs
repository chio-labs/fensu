//! Convert function-contract rows into Python fact model instances.

use pyo3::types::{PyAnyMethods, PyTuple};
use pyo3::{Bound, Py, PyAny, PyResult, Python};

use crate::constants;
use crate::extension::helpers::convert_annotations::location_object;
use crate::extension::helpers::convert_declarations::to_object;
use crate::extension::helpers::model_types::model_type;
use crate::extension::helpers::program::ProgramHandle;
use crate::facts::main::extract_function_contracts::extract_function_contracts;

pub(crate) fn function_contract_facts_object(
    py: Python<'_>,
    program: &ProgramHandle,
    path: &Bound<'_, PyAny>,
) -> PyResult<Option<Py<PyAny>>> {
    let rows = extract_function_contracts(
        program.module(),
        program.index(),
        program.source(),
        program.version(),
    );
    if rows.iter().any(|row| row.annotation.is_none()) {
        return Ok(None);
    }
    let constructor = model_type(py, constants::FUNCTION_CONTRACT_FACT_NAME)?;
    let mut objects: Vec<Py<PyAny>> = Vec::with_capacity(rows.len());
    for row in rows {
        let location = location_object(py, path, row.line, row.column)?;
        let meaningful = match row.meaningful_return {
            Some((line, column)) => location_object(py, path, line, column)?.unbind(),
            None => py.None(),
        };
        let arguments = PyTuple::new(
            py,
            vec![
                to_object(py, row.function_name)?,
                location.unbind(),
                to_object(py, row.category)?,
                to_object(py, row.annotation)?,
                to_object(py, row.contains_yield)?,
                meaningful,
            ],
        )?;
        objects.push(constructor.call1(arguments)?.unbind());
    }
    Ok(Some(PyTuple::new(py, objects)?.into_any().unbind()))
}
