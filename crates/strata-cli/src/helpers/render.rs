use std::fs;
use std::path::Path;

use crate::models::{Fault, ThresholdUse};

const RED: &str = "\x1b[1;31m";
const GREEN: &str = "\x1b[1;32m";
const DIM: &str = "\x1b[2m";
const RESET: &str = "\x1b[0m";

pub(crate) struct ReportRequest<'a> {
    pub(crate) faults: &'a [Fault],
    pub(crate) warnings: &'a [Fault],
    pub(crate) root: &'a Path,
    pub(crate) color: bool,
    pub(crate) show_warnings: bool,
    pub(crate) evaluation_summary: Option<&'a str>,
    pub(crate) applied_exceptions: usize,
    pub(crate) threshold_uses: &'a [ThresholdUse],
}

pub(crate) fn report(request: ReportRequest<'_>) -> String {
    let mut sections = Vec::new();
    for fault in request.faults.iter().chain(request.warnings) {
        sections.push(format_fault(fault, request.root, request.color));
    }
    let noun = if request.faults.len() == 1 {
        "fault"
    } else {
        "faults"
    };
    let mut summary = format!("Found {} {noun}", request.faults.len());
    if request.show_warnings {
        let noun = if request.warnings.len() == 1 {
            "warning"
        } else {
            "warnings"
        };
        summary.push_str(&format!(" and {} {noun}", request.warnings.len()));
    }
    if request.color {
        let style = if request.faults.is_empty() {
            GREEN
        } else {
            RED
        };
        summary = format!("{style}{summary}{RESET}");
    }
    sections.push(summary);
    if let Some(value) = request.evaluation_summary {
        sections.push(if request.color {
            format!("{DIM}{value}{RESET}")
        } else {
            value.to_owned()
        });
    }
    if request.applied_exceptions > 0 {
        let noun = if request.applied_exceptions == 1 {
            "exception"
        } else {
            "exceptions"
        };
        sections.push(format!(
            "Applied {} rule {noun}",
            request.applied_exceptions
        ));
    }
    if !request.threshold_uses.is_empty() {
        let noun = if request.threshold_uses.len() == 1 {
            "override"
        } else {
            "overrides"
        };
        sections.push(format!(
            "Applied {} threshold {noun}",
            request.threshold_uses.len()
        ));
        for use_ in request.threshold_uses {
            sections.push(format!(
                "Threshold override: {}={} path={} pattern={} order={} reason={}",
                use_.threshold,
                use_.effective_value,
                use_.repository_path,
                use_.matched_pattern,
                use_.override_order,
                serde_json::to_string(&use_.reason).expect("serialize reason")
            ));
        }
    }
    format!(
        "{}\n",
        sections
            .join("\n\n")
            .replace("\n\nApplied", "\nApplied")
            .replace("\n\nEvaluation:", "\nEvaluation:")
    )
}

fn format_fault(fault: &Fault, root: &Path, color: bool) -> String {
    let path = fault
        .path
        .strip_prefix(root.to_string_lossy().as_ref())
        .map_or_else(
            || fault.path.clone(),
            |value| value.trim_start_matches('/').to_owned(),
        );
    let line = fault
        .line
        .map_or_else(|| "-".to_owned(), |value| value.to_string());
    let column = fault
        .column
        .map_or_else(|| "-".to_owned(), |value| value.to_string());
    let mut lines = if color {
        vec![
            format!("{RED}{}{RESET}  {}", fault.code, fault.message),
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
                    format!("{DIM}  |{RESET} {padding}{RED}^{RESET}"),
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
        lines.push(if color {
            format!("  {DIM}= {label}:{RESET} {remediation}")
        } else {
            format!("  = {label}: {remediation}")
        });
    } else if fault.warning {
        lines.push(if color {
            format!("  {DIM}= warning{RESET}")
        } else {
            "  = warning".to_owned()
        });
    }
    lines.join("\n")
}

fn source_line(path: &Path, line: u32) -> Option<String> {
    fs::read_to_string(path)
        .ok()?
        .lines()
        .nth(line.saturating_sub(1) as usize)
        .map(str::to_owned)
}
