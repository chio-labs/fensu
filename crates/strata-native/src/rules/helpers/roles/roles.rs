//! Dispatch role-family policy over local path, text, and declaration rows.

use strata_facts::extension::models::ProgramHandle;

use crate::rules::helpers::{role_declarations, role_paths, role_surfaces};
use crate::rules::models::{NativeFaultRow, NativeRuleContext};

pub(crate) fn role_faults(
    program: &ProgramHandle,
    code: &str,
    context: &NativeRuleContext,
) -> Option<Vec<NativeFaultRow>> {
    role_declarations::declaration_faults(program, code, context)
        .or_else(|| role_paths::path_faults(code, context))
        .or_else(|| role_surfaces::surface_faults(program, code, context))
}

pub(super) fn path_name(context: &NativeRuleContext) -> Option<&str> {
    context.relative_parts.last().map(String::as_str)
}

pub(super) fn location_rows(code: &str, locations: &[(u32, u32)]) -> Vec<NativeFaultRow> {
    locations
        .iter()
        .map(|(line, column)| location_fault(code, *line, *column, None))
        .collect()
}

pub(super) fn location_fault(
    code: &str,
    line: u32,
    column: u32,
    message: Option<&str>,
) -> NativeFaultRow {
    NativeFaultRow {
        code: code.to_owned(),
        line,
        column,
        message: message.map(str::to_owned),
        remediation: None,
    }
}

pub(super) fn path_fault(code: &str, message: Option<&str>) -> NativeFaultRow {
    location_fault(code, 0, 0, message)
}
