//! Build deterministic product-neutral reporting counts.

use crate::lifecycle::models::{Finding, FindingSeverity, ReportSummary};

/// Count findings and applied exception mechanisms for reporting.
pub fn report_summary(
    findings: &[Finding],
    applied_suppressions: usize,
    applied_scoped_ignores: usize,
) -> ReportSummary {
    ReportSummary {
        blocking: findings
            .iter()
            .filter(|finding| finding.severity == FindingSeverity::Blocking)
            .count(),
        warnings: findings
            .iter()
            .filter(|finding| finding.severity == FindingSeverity::Warning)
            .count(),
        applied_suppressions,
        applied_scoped_ignores,
    }
}
