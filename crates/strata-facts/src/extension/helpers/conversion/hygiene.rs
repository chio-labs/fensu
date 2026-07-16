//! Convert hygiene and control-flow rows into Python facts.

use pyo3::types::{PyAnyMethods, PyTuple};
use pyo3::{Bound, Py, PyAny, PyResult, Python};

use crate::constants;
use crate::extension::helpers::conversion::declarations::{location_tuple, to_object};
use crate::extension::helpers::conversion::state::source_range_object;
use crate::extension::helpers::gateway::model_types::model_type;
use crate::extension::helpers::gateway::program::ProgramHandle;
use crate::facts::models::ControlFlowRows;

pub(crate) fn hygiene_facts_object(
    py: Python<'_>,
    program: &ProgramHandle,
    path: &Bound<'_, PyAny>,
) -> PyResult<Py<PyAny>> {
    let rows = program.hygiene_rows();
    let constructor = model_type(py, constants::HYGIENE_FACTS_NAME)?;
    let arguments = PyTuple::new(
        py,
        vec![
            location_tuple(py, path, &rows.multiline_docstrings)?,
            location_tuple(py, path, &rows.raw_builtin_raises)?,
            location_tuple(py, path, &rows.assertions)?,
            location_tuple(py, path, &rows.swallowed_exception_probes)?,
            location_tuple(py, path, &rows.unnamed_string_decisions)?,
            location_tuple(py, path, &rows.magic_numeric_comparisons)?,
        ],
    )?;
    Ok(constructor.call1(arguments)?.unbind())
}

pub(crate) fn control_flow_facts_objects(
    py: Python<'_>,
    program: &ProgramHandle,
    path: &Bound<'_, PyAny>,
) -> PyResult<(Py<PyAny>, Py<PyAny>, Py<PyAny>)> {
    let rows: &ControlFlowRows = program.control_flow_rows();
    let conditional_constructor = model_type(py, constants::FUNCTION_CONDITIONAL_FACT_NAME)?;
    let mut conditional_objects: Vec<Py<PyAny>> =
        Vec::with_capacity(rows.function_conditionals.len());
    for row in &rows.function_conditionals {
        let names = PyTuple::new(py, &row.decorator_names)?;
        let range = source_range_object(py, path, &row.range)?;
        conditional_objects.push(
            conditional_constructor
                .call1((to_object(py, &row.function_name)?, names, range))?
                .unbind(),
        );
    }
    let conditionals = PyTuple::new(py, conditional_objects)?.into_any().unbind();
    let comprehensions = location_tuple(py, path, &rows.complex_comprehensions)?;
    let top_level = location_tuple(py, path, &rows.top_level_test_conditionals)?;
    Ok((conditionals, comprehensions, top_level))
}
