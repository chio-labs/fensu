//! Format one fault into styled report lines.

use std::path::Path;

use crate::models::Fault;
use crate::reporting::_helpers::text::{source_line, wrapped_help};
use crate::reporting::constants::{DIM, ORANGE, RESET};

pub(crate) fn format_fault(fault: &Fault, root: &Path, color: bool) -> String {
    let fault_path = Path::new(&fault.path);
    let path = fault_path
        .strip_prefix(root)
        .unwrap_or(fault_path)
        .to_string_lossy()
        .replace('\\', "/")
        .trim_start_matches('/')
        .to_owned();
    let line = fault
        .line
        .map_or_else(|| "-".to_owned(), |value| value.to_string());
    let column = fault
        .column
        .map_or_else(|| "-".to_owned(), |value| value.to_string());
    let mut lines = if color {
        vec![
            format!("{ORANGE}{}{RESET}  {}", fault.code, fault.message),
            format!("{DIM} --> {path}:{line}:{column}{RESET}"),
        ]
    } else {
        vec![
            format!("{}  {}", fault.code, fault.message),
            format!(" --> {path}:{line}:{column}"),
        ]
    };
    if let Some(line_number) = fault.line {
        if let Some(source_line) = source_line(Path::new(&fault.path), line_number) {
            let padding = " ".repeat(fault.column.unwrap_or(0) as usize);
            if color {
                lines.extend([
                    format!("{DIM}  |{RESET}"),
                    format!("{DIM}{line_number} |{RESET} {source_line}"),
                    format!("{DIM}  |{RESET} {padding}{ORANGE}^{RESET}"),
                    format!("{DIM}  |{RESET}"),
                ]);
            } else {
                lines.extend([
                    "  |".to_owned(),
                    format!("{line_number} | {source_line}"),
                    format!("  | {padding}^"),
                    "  |".to_owned(),
                ]);
            }
        }
    }
    if let Some(remediation) = &fault.remediation {
        let label = if fault.warning { "warning" } else { "help" };
        lines.extend(wrapped_help(remediation, label, color));
    } else if fault.warning {
        lines.push(if color {
            format!("  {DIM}= warning{RESET}")
        } else {
            "  = warning".to_owned()
        });
    }
    lines.join("\n")
}
