//! Deterministically order product-neutral findings.

use crate::lifecycle::models::Finding;

/// Return findings ordered by repository location, identity, and stable content.
pub fn sorted_findings(findings: &[Finding]) -> Vec<Finding> {
    let mut sorted = findings.to_vec();
    sorted.sort_by(|left, right| {
        (
            &left.path,
            left.line.unwrap_or(0),
            left.column.unwrap_or(0),
            &left.code,
            &left.symbol,
            &left.message,
            &left.remediation,
            left.severity,
        )
            .cmp(&(
                &right.path,
                right.line.unwrap_or(0),
                right.column.unwrap_or(0),
                &right.code,
                &right.symbol,
                &right.message,
                &right.remediation,
                right.severity,
            ))
    });
    sorted
}
