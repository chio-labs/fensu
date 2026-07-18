//! Annotation-family policy over shared annotation rows.

use strata_facts::facts::models::{AnnotationRows, NamedLocationRow};

use crate::rules::constants::PARAMETER_ANNOTATION_CODE;
use crate::rules::models::NativeFaultRow;

pub(crate) fn parameter_annotation_faults(rows: &AnnotationRows) -> Vec<NativeFaultRow> {
    rows.parameters.iter().map(parameter_fault).collect()
}

fn parameter_fault(row: &NamedLocationRow) -> NativeFaultRow {
    NativeFaultRow {
        code: PARAMETER_ANNOTATION_CODE,
        line: row.line,
        column: row.column,
        message: format!(
            "function parameter '{}' must define a type annotation",
            row.name
        ),
    }
}
