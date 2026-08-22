//! Public lifecycle request, result, suppression, cache, and host models.

use std::path::Path;
use std::time::Duration;

use serde::{Deserialize, Serialize};
use serde_json::Value;

/// Versions whose changes invalidate reusable analysis results.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct RuntimeIdentity {
    pub producer: String,
    pub fact_schema: String,
    pub runtime: String,
    pub rule_pack: String,
    pub configuration: String,
}

/// One repository-relative fact payload in an analysis batch.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct AnalysisInput<Facts> {
    pub path: String,
    pub fingerprint: String,
    pub facts: Facts,
}

/// One versioned request shared by direct Rust and serialized consumers.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct AnalysisBatchRequest<Facts> {
    pub schema_version: u32,
    pub required_capabilities: Vec<String>,
    pub identity: RuntimeIdentity,
    pub inputs: Vec<AnalysisInput<Facts>>,
}

/// Whether a finding blocks the command or is advisory.
#[derive(Clone, Copy, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum FindingSeverity {
    Blocking,
    Warning,
}

/// Product-neutral diagnostic emitted by built-in or custom rules.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Finding {
    pub code: String,
    pub path: String,
    pub line: Option<u32>,
    pub column: Option<u32>,
    pub symbol: Option<String>,
    pub message: String,
    pub remediation: Option<String>,
    pub severity: FindingSeverity,
}

/// Deterministic aggregate counts for machine and human reporting.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ReportSummary {
    pub blocking: usize,
    pub warnings: usize,
    pub applied_suppressions: usize,
    pub applied_scoped_ignores: usize,
}

/// Versioned response returned after evaluating one batch.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct AnalysisBatchResponse {
    pub schema_version: u32,
    pub capabilities: Vec<String>,
    pub cache_identity: String,
    pub findings: Vec<Finding>,
    pub report: ReportSummary,
}

/// Exact, stale-checked suppression of one file or symbol finding.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ExactSuppression {
    pub code: String,
    pub path: String,
    pub symbol: Option<String>,
    pub reason: String,
}

/// Deliberately broad path-scoped ignore, kept distinct from suppressions.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct ScopedIgnore {
    pub selectors: Vec<String>,
    pub paths: Vec<String>,
    pub reason: String,
}

/// Findings retained after applying both exception mechanisms.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct SuppressionResult {
    pub findings: Vec<Finding>,
    pub applied_suppressions: usize,
    pub applied_scoped_ignores: usize,
}

/// Named inputs for exact and scoped suppression application.
#[derive(Debug)]
pub struct ApplySuppressionsRequest<'a, Grammar> {
    pub findings: Vec<Finding>,
    pub evaluated_codes: &'a [String],
    pub suppressions: &'a [ExactSuppression],
    pub scoped_ignores: &'a [ScopedIgnore],
    pub grammar: &'a Grammar,
}

/// Outcome of reading one reusable cache namespace.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum CacheRead<T> {
    Hit(T),
    Miss,
    Invalidated,
}

/// Versioned request sent to an isolated custom-rule process.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct CustomHostRequest<Payload> {
    pub protocol: u32,
    pub runtime_version: String,
    pub payload: Payload,
}

/// Process launch details and mandatory output bounds kept outside the wire request.
#[derive(Debug)]
pub struct CustomHostInvocation<'a, Payload> {
    pub program: &'a Path,
    pub arguments: &'a [String],
    pub timeout: Duration,
    pub output_limits: CustomHostOutputLimits,
    pub request: &'a CustomHostRequest<Payload>,
}

/// Explicit memory bounds for output captured from one custom host.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct CustomHostOutputLimits {
    pub stdout_bytes: usize,
    pub stderr_bytes: usize,
}

impl Default for CustomHostOutputLimits {
    fn default() -> Self {
        Self {
            stdout_bytes: 16 * 1_024 * 1_024,
            stderr_bytes: 1_024 * 1_024,
        }
    }
}

/// Versioned response containing exactly one successful payload or non-empty error.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct CustomHostResponse<Payload> {
    pub protocol: u32,
    pub runtime_version: String,
    pub error: Option<String>,
    pub payload: Option<Payload>,
    pub messages: Vec<String>,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct RawCustomHostResponse {
    pub(crate) protocol: u32,
    pub(crate) runtime_version: String,
    pub(crate) error: Option<String>,
    pub(crate) payload: Option<Value>,
    pub(crate) messages: Vec<String>,
}

/// Schema-v2 ownership marker used to detect foreign, stale, or edited generated skills.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct SkillOwnership {
    pub schema: u32,
    pub owner: String,
    pub identity: String,
    pub input_fingerprint: String,
    pub content_fingerprint: String,
}

/// Result of checking generated skill content against its current owner and inputs.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum SkillFreshness {
    Fresh,
    Missing,
    Unowned,
    Stale,
    Divergent,
    Malformed,
}
