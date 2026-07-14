//! Convert function-metric and parameter-mutation rows into Python facts.

use pyo3::types::{PyAnyMethods, PyTuple};
use pyo3::{Bound, Py, PyAny, PyResult, Python};

use crate::constants;
use crate::extension::helpers::conversion::annotations::location_object;
use crate::extension::helpers::conversion::declarations::to_object;
use crate::extension::helpers::gateway::model_types::model_type;
use crate::extension::helpers::gateway::program::ProgramHandle;
use crate::facts::main::extract_functions::extract_functions;
use crate::facts::main::extract_parameter_mutations::extract_parameter_mutations;

pub(crate) fn function_facts_object(
    py: Python<'_>,
    program: &ProgramHandle,
    path: &Bound<'_, PyAny>,
) -> PyResult<Py<PyAny>> {
    let (rows, top_level_slots) =
        extract_functions(program.module(), program.index(), program.source());
    let constructor = model_type(py, constants::FUNCTION_METRIC_FACT_NAME)?;
    let mut objects: Vec<Py<PyAny>> = Vec::with_capacity(rows.len());
    for row in &rows {
        let arguments = PyTuple::new(
            py,
            vec![
                location_object(py, path, row.line, row.column)?.unbind(),
                to_object(py, &row.name)?,
                to_object(py, row.statement_count)?,
                to_object(py, row.distinct_call_count)?,
                to_object(py, row.assigned_local_count)?,
                to_object(py, row.parameter_count)?,
                to_object(py, row.positional_parameter_count)?,
                to_object(py, row.dunder)?,
            ],
        )?;
        objects.push(constructor.call1(arguments)?.unbind());
    }
    let mut top_level: Vec<Py<PyAny>> = Vec::with_capacity(top_level_slots.len());
    for slot in top_level_slots {
        if let Some(fact) = objects.get(slot) {
            top_level.push(fact.clone_ref(py));
        }
    }
    let facts_constructor = model_type(py, constants::FUNCTION_FACTS_NAME)?;
    let functions_tuple = PyTuple::new(py, objects)?;
    let top_level_tuple = PyTuple::new(py, top_level)?;
    Ok(facts_constructor
        .call1((functions_tuple, top_level_tuple))?
        .unbind())
}

pub(crate) fn parameter_mutation_facts_object(
    py: Python<'_>,
    program: &ProgramHandle,
    path: &Bound<'_, PyAny>,
) -> PyResult<Py<PyAny>> {
    let rows = extract_parameter_mutations(program.module(), program.index(), program.source());
    let constructor = model_type(py, constants::PARAMETER_MUTATION_FACT_NAME)?;
    let mut objects: Vec<Py<PyAny>> = Vec::with_capacity(rows.len());
    for row in rows {
        let arguments = PyTuple::new(
            py,
            vec![
                to_object(py, row.function_name)?,
                to_object(py, row.parameter_name)?,
                location_object(py, path, row.line, row.column)?.unbind(),
                to_object(py, row.returned)?,
                to_object(py, row.dunder)?,
                to_object(py, row.setter)?,
            ],
        )?;
        objects.push(constructor.call1(arguments)?.unbind());
    }
    Ok(PyTuple::new(py, objects)?.into_any().unbind())
}

pub(crate) fn dataclass_facts_object(
    py: Python<'_>,
    program: &ProgramHandle,
    path: &Bound<'_, PyAny>,
) -> PyResult<Py<PyAny>> {
    let rows = crate::facts::main::extract_dataclasses::extract_dataclasses(
        program.module(),
        program.index(),
        program.source(),
    );
    let constructor = model_type(py, constants::DATACLASS_FACT_NAME)?;
    let mut objects: Vec<Py<PyAny>> = Vec::with_capacity(rows.len());
    for row in rows {
        let fields = pyo3::types::PyFrozenSet::new(py, &row.field_names)?;
        let arguments = PyTuple::new(
            py,
            vec![
                to_object(py, row.name)?,
                location_object(py, path, row.line, row.column)?.unbind(),
                fields.into_any().unbind(),
                to_object(py, row.frozen)?,
                to_object(py, row.shape_candidate)?,
            ],
        )?;
        objects.push(constructor.call1(arguments)?.unbind());
    }
    Ok(PyTuple::new(py, objects)?.into_any().unbind())
}

pub(crate) fn project_facts_objects(
    py: Python<'_>,
    program: &ProgramHandle,
    path: &Bound<'_, PyAny>,
) -> PyResult<(Py<PyAny>, Py<PyAny>)> {
    let (functions, calls) = crate::facts::main::extract_project_facts::extract_project_facts(
        program.module(),
        program.index(),
        program.source(),
    );
    let function_constructor = model_type(py, constants::PROJECT_FUNCTION_FACT_NAME)?;
    let mut function_objects: Vec<Py<PyAny>> = Vec::with_capacity(functions.len());
    for row in functions {
        function_objects.push(
            function_constructor
                .call1((row.name, row.meaningful_result))?
                .unbind(),
        );
    }
    let call_constructor = model_type(py, constants::DISCARDED_PROJECT_CALL_FACT_NAME)?;
    let mut call_objects: Vec<Py<PyAny>> = Vec::with_capacity(calls.len());
    for row in calls {
        call_objects.push(
            call_constructor
                .call1((
                    location_object(py, path, row.line, row.column)?,
                    row.module_name,
                    row.function_name,
                ))?
                .unbind(),
        );
    }
    let calls_tuple = PyTuple::new(py, call_objects)?;
    let project_calls = model_type(py, constants::PROJECT_CALL_FACTS_NAME)?
        .call1((calls_tuple,))?
        .unbind();
    Ok((
        PyTuple::new(py, function_objects)?.into_any().unbind(),
        project_calls,
    ))
}
