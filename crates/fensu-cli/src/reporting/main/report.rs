//! Render one complete check or memory report.

use crate::reporting::constants::{DIM, GREEN, ORANGE, RESET};
use crate::reporting::helpers::faults::format_fault;
use crate::reporting::models::ReportRequest;

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
            ORANGE
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
