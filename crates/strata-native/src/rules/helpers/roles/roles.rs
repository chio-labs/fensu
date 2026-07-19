//! Dispatch role-family policy over local path, text, and declaration rows.

use strata_facts::extension::models::ProgramHandle;

use crate::rules::helpers::{role_declarations, role_paths, role_project_layout, role_surfaces};
use crate::rules::models::{NativeFaultRow, NativeRuleContext};

const CORE_RULE_CODE_LENGTH: usize = 6;
const MINIMUM_CUSTOM_RULE_CODE_LENGTH: usize = 2;

pub(crate) fn role_faults(
    program: &ProgramHandle,
    code: &str,
    context: &NativeRuleContext,
) -> Option<Vec<NativeFaultRow>> {
    role_declarations::declaration_faults(program, code, context)
        .or_else(|| role_project_layout::project_layout_faults(code, context))
        .or_else(|| role_paths::path_faults(code, context))
        .or_else(|| role_surfaces::surface_faults(program, code, context))
}

pub(crate) fn is_rule_code(value: &str) -> bool {
    let bytes = value.as_bytes();
    let core = bytes.len() == CORE_RULE_CODE_LENGTH
        && bytes.starts_with(b"SF")
        && bytes[2].is_ascii_uppercase()
        && bytes[3..].iter().all(u8::is_ascii_digit);
    let custom = bytes.first() == Some(&b'X')
        && bytes.len() >= MINIMUM_CUSTOM_RULE_CODE_LENGTH
        && bytes[1..]
            .iter()
            .all(|byte| byte.is_ascii_uppercase() || byte.is_ascii_digit())
        && bytes[1..].iter().any(u8::is_ascii_digit)
        && bytes[1..]
            .iter()
            .skip_while(|byte| byte.is_ascii_uppercase())
            .all(u8::is_ascii_digit);
    core || custom
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
        path: None,
    }
}

pub(super) fn path_fault(code: &str, message: Option<&str>) -> NativeFaultRow {
    location_fault(code, 0, 0, message)
}
