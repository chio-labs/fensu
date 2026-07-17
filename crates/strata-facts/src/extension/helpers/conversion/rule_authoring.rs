//! Convert rule-authoring rows into public Python fact models.

use pyo3::types::{PyAnyMethods, PyBytes, PyComplex, PyTuple};
use pyo3::{Bound, Py, PyAny, PyResult, Python};

use crate::constants;
use crate::extension::helpers::conversion::annotations::location_object;
use crate::extension::helpers::conversion::declarations::to_object;
use crate::extension::helpers::gateway::model_types::model_type;
use crate::extension::helpers::gateway::program::ProgramHandle;
use crate::facts::models::{
    DefinitionIdentityRow, LiteralArgumentRow, ParameterMutationOccurrenceRow,
    QualifiedReferenceRow,
};
use crate::facts::types::LiteralValueRow;

pub(crate) fn class_declaration_facts_object(
    py: Python<'_>,
    program: &ProgramHandle,
    path: &Bound<'_, PyAny>,
) -> PyResult<Py<PyAny>> {
    let class_constructor = model_type(py, constants::CLASS_DECLARATION_FACT_NAME)?;
    let method_constructor = model_type(py, constants::CLASS_METHOD_FACT_NAME)?;
    let mut classes = Vec::with_capacity(program.class_declaration_rows().len());
    for row in program.class_declaration_rows() {
        let owner = definition_identity_object(
            py,
            path,
            &DefinitionIdentityRow {
                name: row.name.clone(),
                line: row.line,
                column: row.column,
            },
        )?;
        let mut methods = Vec::with_capacity(row.methods.len());
        for method in &row.methods {
            methods.push(
                method_constructor
                    .call1((
                        &method.name,
                        PyTuple::new(py, &method.decorator_names)?,
                        location_object(py, path, method.line, method.column)?,
                        owner.clone_ref(py),
                    ))?
                    .unbind(),
            );
        }
        classes.push(
            class_constructor
                .call1((
                    &row.name,
                    PyTuple::new(py, &row.base_names)?,
                    PyTuple::new(py, &row.decorator_names)?,
                    location_object(py, path, row.line, row.column)?,
                    row.top_level,
                    PyTuple::new(py, methods)?,
                ))?
                .unbind(),
        );
    }
    Ok(PyTuple::new(py, classes)?.into_any().unbind())
}

pub(crate) fn assignment_reference_facts_object(
    py: Python<'_>,
    program: &ProgramHandle,
    path: &Bound<'_, PyAny>,
) -> PyResult<Py<PyAny>> {
    let constructor = model_type(py, constants::ASSIGNMENT_REFERENCE_FACT_NAME)?;
    let mut facts = Vec::with_capacity(program.assignment_reference_rows().len());
    for row in program.assignment_reference_rows() {
        facts.push(
            constructor
                .call1((
                    location_object(py, path, row.line, row.column)?,
                    optional_identity_object(py, path, row.owning_class.as_ref())?,
                    optional_identity_object(py, path, row.owning_function.as_ref())?,
                    PyTuple::new(py, &row.target_names)?,
                    optional_reference_object(py, row.value_reference.as_ref())?,
                ))?
                .unbind(),
        );
    }
    Ok(PyTuple::new(py, facts)?.into_any().unbind())
}

pub(crate) fn named_call_facts_object(
    py: Python<'_>,
    program: &ProgramHandle,
    path: &Bound<'_, PyAny>,
) -> PyResult<Py<PyAny>> {
    let constructor = model_type(py, constants::NAMED_CALL_FACT_NAME)?;
    let mut facts = Vec::with_capacity(program.named_call_rows().len());
    for row in program.named_call_rows() {
        facts.push(
            constructor
                .call1((
                    location_object(py, path, row.line, row.column)?,
                    row.name.as_deref(),
                    qualified_reference_object(py, &row.reference)?,
                    optional_identity_object(py, path, row.owning_class.as_ref())?,
                    optional_identity_object(py, path, row.owning_function.as_ref())?,
                    identity_tuple(py, path, &row.enclosing_classes)?,
                    identity_tuple(py, path, &row.enclosing_functions)?,
                    row.inside_loop,
                    literal_argument_tuple(py, &row.literal_arguments)?,
                    row.bare_expression,
                    row.super_call,
                ))?
                .unbind(),
        );
    }
    Ok(PyTuple::new(py, facts)?.into_any().unbind())
}

pub(crate) fn local_call_edge_facts_object(
    py: Python<'_>,
    program: &ProgramHandle,
    path: &Bound<'_, PyAny>,
) -> PyResult<Py<PyAny>> {
    let constructor = model_type(py, constants::LOCAL_CALL_EDGE_FACT_NAME)?;
    let mut facts = Vec::with_capacity(program.local_call_edge_rows().len());
    for row in program.local_call_edge_rows() {
        facts.push(
            constructor
                .call1((
                    location_object(py, path, row.line, row.column)?,
                    definition_identity_object(py, path, &row.caller)?,
                    optional_identity_object(py, path, row.caller_class.as_ref())?,
                    qualified_reference_object(py, &row.callee)?,
                    row.inside_loop,
                ))?
                .unbind(),
        );
    }
    Ok(PyTuple::new(py, facts)?.into_any().unbind())
}

pub(crate) fn comparison_facts_object(
    py: Python<'_>,
    program: &ProgramHandle,
    path: &Bound<'_, PyAny>,
) -> PyResult<Py<PyAny>> {
    let constructor = model_type(py, constants::COMPARISON_FACT_NAME)?;
    let mut facts = Vec::with_capacity(program.comparison_rows().len());
    for row in program.comparison_rows() {
        let mut operands = Vec::with_capacity(row.operand_references.len());
        for reference in &row.operand_references {
            operands.push(optional_reference_object(py, reference.as_ref())?);
        }
        facts.push(
            constructor
                .call1((
                    location_object(py, path, row.line, row.column)?,
                    PyTuple::new(py, operands)?,
                ))?
                .unbind(),
        );
    }
    Ok(PyTuple::new(py, facts)?.into_any().unbind())
}

pub(crate) fn parameter_mutation_occurrence_facts_object(
    py: Python<'_>,
    program: &ProgramHandle,
    path: &Bound<'_, PyAny>,
) -> PyResult<Py<PyAny>> {
    let rows: &[ParameterMutationOccurrenceRow] = program.parameter_mutation_occurrence_rows();
    let constructor = model_type(py, constants::PARAMETER_MUTATION_OCCURRENCE_FACT_NAME)?;
    let mut facts = Vec::with_capacity(rows.len());
    for row in rows {
        facts.push(
            constructor
                .call1((
                    &row.function_name,
                    &row.parameter_name,
                    &row.parameter_kind,
                    location_object(py, path, row.line, row.column)?,
                    row.returned,
                    row.dunder,
                    row.setter,
                ))?
                .unbind(),
        );
    }
    Ok(PyTuple::new(py, facts)?.into_any().unbind())
}

fn definition_identity_object(
    py: Python<'_>,
    path: &Bound<'_, PyAny>,
    row: &DefinitionIdentityRow,
) -> PyResult<Py<PyAny>> {
    Ok(model_type(py, constants::DEFINITION_IDENTITY_NAME)?
        .call1((&row.name, location_object(py, path, row.line, row.column)?))?
        .unbind())
}

fn optional_identity_object(
    py: Python<'_>,
    path: &Bound<'_, PyAny>,
    row: Option<&DefinitionIdentityRow>,
) -> PyResult<Py<PyAny>> {
    match row {
        Some(value) => definition_identity_object(py, path, value),
        None => Ok(py.None()),
    }
}

fn identity_tuple(
    py: Python<'_>,
    path: &Bound<'_, PyAny>,
    rows: &[DefinitionIdentityRow],
) -> PyResult<Py<PyAny>> {
    let mut objects = Vec::with_capacity(rows.len());
    for row in rows {
        objects.push(definition_identity_object(py, path, row)?);
    }
    Ok(PyTuple::new(py, objects)?.into_any().unbind())
}

fn qualified_reference_object(py: Python<'_>, row: &QualifiedReferenceRow) -> PyResult<Py<PyAny>> {
    Ok(model_type(py, constants::QUALIFIED_REFERENCE_FACT_NAME)?
        .call1((
            &row.kind,
            row.name.as_deref(),
            row.base_name.as_deref(),
            row.receiver_base_name.as_deref(),
            PyTuple::new(py, &row.parts)?,
        ))?
        .unbind())
}

fn optional_reference_object(
    py: Python<'_>,
    row: Option<&QualifiedReferenceRow>,
) -> PyResult<Py<PyAny>> {
    match row {
        Some(value) => qualified_reference_object(py, value),
        None => Ok(py.None()),
    }
}

fn literal_argument_tuple(py: Python<'_>, rows: &[LiteralArgumentRow]) -> PyResult<Py<PyAny>> {
    let constructor = model_type(py, constants::LITERAL_ARGUMENT_FACT_NAME)?;
    let mut objects = Vec::with_capacity(rows.len());
    for row in rows {
        objects.push(
            constructor
                .call1((
                    row.position,
                    &row.kind,
                    literal_value_object(py, &row.value)?,
                ))?
                .unbind(),
        );
    }
    Ok(PyTuple::new(py, objects)?.into_any().unbind())
}

fn literal_value_object(py: Python<'_>, value: &LiteralValueRow) -> PyResult<Py<PyAny>> {
    match value {
        LiteralValueRow::StringSource(value) => Ok(py
            .import("ast")?
            .getattr("literal_eval")?
            .call1((format!("({value})"),))?
            .unbind()),
        LiteralValueRow::Bytes(value) => Ok(PyBytes::new(py, value).into_any().unbind()),
        LiteralValueRow::Integer(value) => Ok(py
            .import("builtins")?
            .getattr("int")?
            .call1((value, 0))?
            .unbind()),
        LiteralValueRow::Float(value) => to_object(py, *value),
        LiteralValueRow::Complex { real, imag } => Ok(PyComplex::from_doubles(py, *real, *imag)
            .into_any()
            .unbind()),
        LiteralValueRow::Boolean(value) => to_object(py, *value),
        LiteralValueRow::None => Ok(py.None()),
    }
}
