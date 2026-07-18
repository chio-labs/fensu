//! Tests-family policy over shared per-file fact rows.

use strata_facts::extension::models::ProgramHandle;

use crate::rules::constants::{TEST_ABSOLUTE_IMPORTS_CODE, TEST_NO_COMPLEX_COMPREHENSIONS_CODE};
use crate::rules::models::NativeFaultRow;

pub(crate) fn test_faults(program: &ProgramHandle, code: &str) -> Option<Vec<NativeFaultRow>> {
    let faults = match code {
        TEST_ABSOLUTE_IMPORTS_CODE => program
            .reference_rows()
            .imports
            .iter()
            .filter(|row| row.from_import && row.relative_level > 0)
            .map(|row| location_fault(code, row.line, row.column))
            .collect(),
        TEST_NO_COMPLEX_COMPREHENSIONS_CODE => program
            .control_flow_rows()
            .complex_comprehensions
            .iter()
            .map(|(line, column)| location_fault(code, *line, *column))
            .collect(),
        _ => return None,
    };
    Some(faults)
}

fn location_fault(code: &str, line: u32, column: u32) -> NativeFaultRow {
    NativeFaultRow {
        code: code.to_owned(),
        line,
        column,
        message: None,
        remediation: None,
    }
}
