//! Convert native mapping rows into compact Python tuples.

use pyo3::types::PyTuple;
use pyo3::{Py, PyAny, PyResult, Python};

use crate::extension::helpers::conversion::declarations::to_object;
use crate::facts::mapping::models::{
    MappingAttributeRow, MappingCallRow, MappingClassRow, MappingExpressionRow, MappingFunctionRow,
    MappingImportRow, MappingParameterRow, MappingRows, MappingStatementRow,
};

pub(crate) fn mapping_rows_object(py: Python<'_>, rows: &MappingRows) -> PyResult<Py<PyAny>> {
    tuple_object(
        py,
        vec![
            imports_object(py, &rows.runtime_imports)?,
            imports_object(py, &rows.annotation_imports)?,
            functions_object(py, &rows.functions)?,
            classes_object(py, &rows.classes)?,
        ],
    )
}

fn expression_object(py: Python<'_>, row: &MappingExpressionRow) -> PyResult<Py<PyAny>> {
    let child = match &row.child {
        Some(value) => expression_object(py, value)?,
        None => py.None(),
    };
    tuple_object(
        py,
        vec![
            to_object(py, &row.kind)?,
            to_object(py, &row.spelling)?,
            to_object(py, &row.parts)?,
            child,
            to_object(py, row.string_value.as_deref())?,
        ],
    )
}

fn imports_object(py: Python<'_>, rows: &[MappingImportRow]) -> PyResult<Py<PyAny>> {
    let mut objects = Vec::with_capacity(rows.len());
    for row in rows {
        let aliases = tuple_object(
            py,
            row.aliases
                .iter()
                .map(|alias| {
                    tuple_object(
                        py,
                        vec![
                            to_object(py, &alias.name)?,
                            to_object(py, alias.asname.as_deref())?,
                        ],
                    )
                })
                .collect::<PyResult<Vec<_>>>()?,
        )?;
        objects.push(tuple_object(
            py,
            vec![
                to_object(py, row.module.as_deref())?,
                to_object(py, row.level)?,
                aliases,
                to_object(py, row.from_import)?,
            ],
        )?);
    }
    tuple_object(py, objects)
}

fn functions_object(py: Python<'_>, rows: &[MappingFunctionRow]) -> PyResult<Py<PyAny>> {
    let mut objects = Vec::with_capacity(rows.len());
    for row in rows {
        let parameters = parameters_object(py, &row.parameters)?;
        let returns = match &row.returns {
            Some(value) => expression_object(py, value)?,
            None => py.None(),
        };
        let statements = statements_object(py, &row.statements)?;
        objects.push(tuple_object(
            py,
            vec![
                to_object(py, &row.name)?,
                to_object(py, row.line)?,
                to_object(py, row.owning_class.as_deref())?,
                parameters,
                returns,
                statements,
            ],
        )?);
    }
    tuple_object(py, objects)
}

fn parameters_object(py: Python<'_>, rows: &[MappingParameterRow]) -> PyResult<Py<PyAny>> {
    let mut objects = Vec::with_capacity(rows.len());
    for row in rows {
        let annotation = match &row.annotation {
            Some(value) => expression_object(py, value)?,
            None => py.None(),
        };
        objects.push(tuple_object(
            py,
            vec![to_object(py, &row.name)?, annotation],
        )?);
    }
    tuple_object(py, objects)
}

fn statements_object(py: Python<'_>, rows: &[MappingStatementRow]) -> PyResult<Py<PyAny>> {
    let mut objects = Vec::with_capacity(rows.len());
    for row in rows {
        let annotation = match &row.binding_annotation {
            Some(value) => expression_object(py, value)?,
            None => py.None(),
        };
        let value = match &row.binding_value {
            Some(value) => expression_object(py, value)?,
            None => py.None(),
        };
        objects.push(tuple_object(
            py,
            vec![
                to_object(py, row.control_flow)?,
                to_object(py, &row.assigned_names)?,
                to_object(py, row.binding_name.as_deref())?,
                annotation,
                value,
                calls_object(py, &row.calls)?,
            ],
        )?);
    }
    tuple_object(py, objects)
}

fn calls_object(py: Python<'_>, rows: &[MappingCallRow]) -> PyResult<Py<PyAny>> {
    let mut objects = Vec::with_capacity(rows.len());
    for row in rows {
        objects.push(tuple_object(
            py,
            vec![
                expression_object(py, &row.callee)?,
                to_object(py, row.line)?,
            ],
        )?);
    }
    tuple_object(py, objects)
}

fn classes_object(py: Python<'_>, rows: &[MappingClassRow]) -> PyResult<Py<PyAny>> {
    let mut objects = Vec::with_capacity(rows.len());
    for row in rows {
        objects.push(tuple_object(
            py,
            vec![
                to_object(py, &row.name)?,
                to_object(py, row.line)?,
                tuple_object(
                    py,
                    row.bases
                        .iter()
                        .map(|base| expression_object(py, base))
                        .collect::<PyResult<Vec<_>>>()?,
                )?,
                attributes_object(py, &row.class_attributes)?,
                attributes_object(py, &row.instance_attributes)?,
            ],
        )?);
    }
    tuple_object(py, objects)
}

fn attributes_object(py: Python<'_>, rows: &[MappingAttributeRow]) -> PyResult<Py<PyAny>> {
    let mut objects = Vec::with_capacity(rows.len());
    for row in rows {
        objects.push(tuple_object(
            py,
            vec![
                to_object(py, &row.name)?,
                expression_object(py, &row.expression)?,
                to_object(py, row.annotation)?,
            ],
        )?);
    }
    tuple_object(py, objects)
}

fn tuple_object(py: Python<'_>, values: Vec<Py<PyAny>>) -> PyResult<Py<PyAny>> {
    Ok(PyTuple::new(py, values)?.into_any().unbind())
}
