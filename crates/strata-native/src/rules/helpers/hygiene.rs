//! Hygiene-family policy over shared fact rows.

use strata_facts::extension::models::ProgramHandle;

use crate::rules::constants::{
    NO_ASSERT_IN_RUNTIME_CODE, NO_COMPLEX_COMPREHENSIONS_IN_TOOLING_CODE,
    NO_IMPORT_TIME_SIDE_EFFECTS_CODE, NO_MAGIC_NUMERIC_COMPARISONS_CODE, NO_RAW_BUILTIN_RAISE_CODE,
    NO_STANDALONE_COMMENTS_CODE, NO_SWALLOWED_EXCEPTION_PROBE_CODE,
    NO_UNNAMED_STRING_DECISIONS_CODE, SINGLE_LINE_DOCSTRINGS_CODE,
};
use crate::rules::models::NativeFaultRow;

const TOOLING_SCOPE: &str = "tooling";
const COMMENT_ALLOWED_PREFIXES: &[&str] = &[
    "#!",
    "# -*-",
    "# coding:",
    "# noqa",
    "# type:",
    "# pyright:",
    "# pylint:",
    "# pragma:",
];

pub(crate) fn hygiene_faults(
    program: &ProgramHandle,
    code: &str,
    scope: &str,
) -> Option<Vec<NativeFaultRow>> {
    let rows = program.hygiene_rows();
    let faults = match code {
        SINGLE_LINE_DOCSTRINGS_CODE => location_faults(code, &rows.multiline_docstrings),
        NO_STANDALONE_COMMENTS_CODE => program
            .comment_rows()
            .iter()
            .filter(|row| {
                !COMMENT_ALLOWED_PREFIXES
                    .iter()
                    .any(|prefix| row.text.starts_with(prefix))
            })
            .map(|row| location_fault(code, row.line, row.column))
            .collect(),
        NO_RAW_BUILTIN_RAISE_CODE => location_faults(code, &rows.raw_builtin_raises),
        NO_ASSERT_IN_RUNTIME_CODE => location_faults(code, &rows.assertions),
        NO_SWALLOWED_EXCEPTION_PROBE_CODE => {
            location_faults(code, &rows.swallowed_exception_probes)
        }
        NO_COMPLEX_COMPREHENSIONS_IN_TOOLING_CODE if scope == TOOLING_SCOPE => {
            location_faults(code, &program.control_flow_rows().complex_comprehensions)
        }
        NO_COMPLEX_COMPREHENSIONS_IN_TOOLING_CODE => Vec::new(),
        NO_UNNAMED_STRING_DECISIONS_CODE => location_faults(code, &rows.unnamed_string_decisions),
        NO_MAGIC_NUMERIC_COMPARISONS_CODE => location_faults(code, &rows.magic_numeric_comparisons),
        NO_IMPORT_TIME_SIDE_EFFECTS_CODE => {
            location_faults(code, &program.declaration_rows().import_time_call_locations)
        }
        _ => return None,
    };
    Some(faults)
}

fn location_faults(code: &str, locations: &[(u32, u32)]) -> Vec<NativeFaultRow> {
    locations
        .iter()
        .map(|(line, column)| location_fault(code, *line, *column))
        .collect()
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
