//! Shape-family policy over shared fact rows.

use strata_facts::extension::models::ProgramHandle;

use crate::rules::constants::{
    DEFAULT_MUTATION_RETURN_CODE, NO_COMPLEX_COMPREHENSIONS_CODE, NO_OUTER_STATE_MUTATION_CODE,
};
use crate::rules::models::NativeFaultRow;

pub(crate) fn shape_faults(program: &ProgramHandle, code: &str) -> Option<Vec<NativeFaultRow>> {
    let faults = match code {
        DEFAULT_MUTATION_RETURN_CODE => program
            .parameter_mutation_rows()
            .iter()
            .filter(|row| !row.dunder && !row.setter && !row.returned)
            .map(|row| location_fault(code, row.line, row.column))
            .collect(),
        NO_OUTER_STATE_MUTATION_CODE => program
            .outer_state_mutation_rows()
            .iter()
            .map(|row| location_fault(code, row.start_line, row.start_column))
            .collect(),
        NO_COMPLEX_COMPREHENSIONS_CODE => program
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
    }
}
