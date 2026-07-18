//! Role-family policy over shared module-declaration rows.

use strata_facts::extension::models::ProgramHandle;

use crate::rules::constants::PRIVATE_DEFINITION_ORDERING_CODE;
use crate::rules::models::NativeFaultRow;

pub(crate) fn role_faults(program: &ProgramHandle, code: &str) -> Option<Vec<NativeFaultRow>> {
    if code != PRIVATE_DEFINITION_ORDERING_CODE {
        return None;
    }
    let mut faults = Vec::new();
    let mut saw_function = false;
    for row in &program.declaration_rows().statements {
        if row.function_name.is_some() {
            saw_function = true;
            continue;
        }
        if !saw_function {
            continue;
        }
        let message = if row
            .class_name
            .as_ref()
            .is_some_and(|name| name.starts_with('_'))
            && row.dataclass_class
        {
            Some("private dataclasses must appear before top-level functions")
        } else if row
            .assignment_target_names
            .iter()
            .any(|name| name.starts_with('_'))
        {
            Some("private constants must appear before top-level functions")
        } else {
            None
        };
        if let Some(message) = message {
            faults.push(NativeFaultRow {
                code: code.to_owned(),
                line: row.line,
                column: row.column,
                message: Some(message.to_owned()),
                remediation: None,
            });
        }
    }
    Some(faults)
}
