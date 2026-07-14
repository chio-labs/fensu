//! Convert outer-state mutation rows into Python fact model instances.

use pyo3::types::{PyAnyMethods, PyTuple};
use pyo3::{Bound, Py, PyAny, PyResult, Python};

use crate::constants;
use crate::extension::helpers::gateway::model_types::model_type;
use crate::extension::helpers::gateway::program::ProgramHandle;
use crate::facts::main::extract_outer_state_mutations::extract_outer_state_mutations;
use crate::facts::models::SourceRangeRow;

pub(crate) fn outer_state_mutation_facts_object(
    py: Python<'_>,
    program: &ProgramHandle,
    path: &Bound<'_, PyAny>,
) -> PyResult<Py<PyAny>> {
    let rows = extract_outer_state_mutations(program.module(), program.index());
    let constructor = model_type(py, constants::OUTER_STATE_MUTATION_FACT_NAME)?;
    let mut objects: Vec<Py<PyAny>> = Vec::with_capacity(rows.len());
    for row in rows {
        let range = source_range_object(py, path, &row)?;
        objects.push(constructor.call1((range,))?.unbind());
    }
    Ok(PyTuple::new(py, objects)?.into_any().unbind())
}

pub(crate) fn source_range_object<'py>(
    py: Python<'py>,
    path: &Bound<'py, PyAny>,
    row: &SourceRangeRow,
) -> PyResult<Bound<'py, PyAny>> {
    let position_type = model_type(py, constants::SOURCE_POSITION_NAME)?;
    let start = position_type.call1((row.start_line, row.start_column, row.start_offset))?;
    let end = position_type.call1((row.end_line, row.end_column, row.end_offset))?;
    model_type(py, constants::SOURCE_RANGE_NAME)?.call1((path, start, end))
}
