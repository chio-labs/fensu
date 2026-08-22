//! Canonically serialize deterministically ordered findings.

use crate::lifecycle::_helpers::canonical;
use crate::lifecycle::errors::LifecycleError;
use crate::lifecycle::main::sorted_findings::sorted_findings;
use crate::lifecycle::models::Finding;

/// Serialize findings as canonical compact JSON after deterministic sorting.
pub fn serialize_findings(findings: &[Finding]) -> Result<Vec<u8>, LifecycleError> {
    canonical::canonical_json(&sorted_findings(findings))
}
