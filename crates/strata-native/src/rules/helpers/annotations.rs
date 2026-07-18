//! Annotation-family policy over shared annotation rows.

use strata_facts::facts::models::{AnnotationRows, NamedLocationRow};

use crate::rules::constants::{
    CLASS_ATTRIBUTE_ANNOTATION_CODE, LOCAL_VARIABLE_ANNOTATION_CODE,
    MODULE_VARIABLE_ANNOTATION_CODE, PARAMETER_ANNOTATION_CODE, RETURN_ANNOTATION_CODE,
};
use crate::rules::models::NativeFaultRow;

pub(crate) fn parameter_annotation_faults(rows: &AnnotationRows) -> Vec<NativeFaultRow> {
    rows.parameters.iter().map(parameter_fault).collect()
}

pub(crate) fn return_annotation_faults(rows: &AnnotationRows) -> Vec<NativeFaultRow> {
    rows.returns
        .iter()
        .map(|row| NativeFaultRow {
            code: RETURN_ANNOTATION_CODE.to_owned(),
            line: row.line,
            column: row.column,
            message: Some(format!(
                "function '{}' must define a return type annotation",
                row.name
            )),
            remediation: None,
        })
        .collect()
}

pub(crate) fn module_variable_annotation_faults(rows: &AnnotationRows) -> Vec<NativeFaultRow> {
    variable_faults(
        &rows.module_variables,
        MODULE_VARIABLE_ANNOTATION_CODE,
        "module-level variable",
    )
}

pub(crate) fn class_attribute_annotation_faults(rows: &AnnotationRows) -> Vec<NativeFaultRow> {
    variable_faults(
        &rows.class_attributes,
        CLASS_ATTRIBUTE_ANNOTATION_CODE,
        "class attribute",
    )
}

pub(crate) fn local_variable_annotation_faults(rows: &AnnotationRows) -> Vec<NativeFaultRow> {
    rows.locals
        .iter()
        .filter(|row| !row.scalar_literal)
        .map(|row| NativeFaultRow {
            code: LOCAL_VARIABLE_ANNOTATION_CODE.to_owned(),
            line: row.line,
            column: row.column,
            message: Some(format!(
                "local variable '{}' must define a type annotation on first binding",
                row.name
            )),
            remediation: None,
        })
        .collect()
}

fn parameter_fault(row: &NamedLocationRow) -> NativeFaultRow {
    NativeFaultRow {
        code: PARAMETER_ANNOTATION_CODE.to_owned(),
        line: row.line,
        column: row.column,
        message: Some(format!(
            "function parameter '{}' must define a type annotation",
            row.name
        )),
        remediation: None,
    }
}

fn variable_faults(
    rows: &[NamedLocationRow],
    code: &'static str,
    subject: &str,
) -> Vec<NativeFaultRow> {
    rows.iter()
        .map(|row| NativeFaultRow {
            code: code.to_owned(),
            line: row.line,
            column: row.column,
            message: Some(format!(
                "{subject} '{}' must define a type annotation",
                row.name
            )),
            remediation: None,
        })
        .collect()
}
