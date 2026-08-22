//! Validate, negotiate, and evaluate one versioned analysis batch.

use std::collections::{BTreeSet, HashSet};

use serde::Serialize;

use crate::lifecycle::_helpers::canonical;
use crate::lifecycle::_helpers::paths::validate_repository_path;
use crate::lifecycle::constants::ANALYSIS_BATCH_SCHEMA_VERSION;
use crate::lifecycle::errors::LifecycleError;
use crate::lifecycle::main::report_summary::report_summary;
use crate::lifecycle::main::sorted_findings::sorted_findings;
use crate::lifecycle::models::{AnalysisBatchRequest, AnalysisBatchResponse, Finding};

/// Evaluate a consumer-owned fact batch after protocol and capability negotiation.
pub fn evaluate_batch<Facts, Evaluate>(
    request: &AnalysisBatchRequest<Facts>,
    supported_capabilities: &[String],
    evaluate: Evaluate,
) -> Result<AnalysisBatchResponse, LifecycleError>
where
    Facts: Serialize,
    Evaluate: FnOnce(&AnalysisBatchRequest<Facts>) -> Result<Vec<Finding>, LifecycleError>,
{
    if request.schema_version != ANALYSIS_BATCH_SCHEMA_VERSION {
        return Err(LifecycleError::UnsupportedBatchSchema {
            actual: request.schema_version,
            expected: ANALYSIS_BATCH_SCHEMA_VERSION,
        });
    }
    if [
        &request.identity.producer,
        &request.identity.fact_schema,
        &request.identity.runtime,
        &request.identity.rule_pack,
        &request.identity.configuration,
    ]
    .iter()
    .any(|value| value.trim().is_empty())
    {
        return Err(LifecycleError::InvalidConfiguration {
            message: "analysis batch version identities must be non-empty".to_owned(),
        });
    }
    if request
        .required_capabilities
        .iter()
        .any(|capability| capability.trim().is_empty())
        || supported_capabilities
            .iter()
            .any(|capability| capability.trim().is_empty())
    {
        return Err(LifecycleError::InvalidConfiguration {
            message: "analysis capabilities must be non-empty".to_owned(),
        });
    }
    let mut input_paths: HashSet<&str> = HashSet::new();
    for input in &request.inputs {
        validate_repository_path(&input.path)?;
        if !input_paths.insert(&input.path) {
            return Err(LifecycleError::InvalidConfiguration {
                message: format!("duplicate analysis input path: {}", input.path),
            });
        }
    }
    let supported = supported_capabilities.iter().collect::<BTreeSet<_>>();
    let mut missing = request
        .required_capabilities
        .iter()
        .filter(|capability| !supported.contains(capability))
        .cloned()
        .collect::<Vec<_>>();
    missing.sort();
    missing.dedup();
    if !missing.is_empty() {
        return Err(LifecycleError::MissingCapabilities {
            capabilities: missing,
        });
    }
    let mut capabilities = supported_capabilities.to_vec();
    capabilities.sort();
    capabilities.dedup();
    let cache_identity = canonical::batch_fingerprint(request, &capabilities)?;
    let findings = evaluate(request)?;
    for finding in &findings {
        validate_repository_path(&finding.path)?;
    }
    let findings = sorted_findings(&findings);
    let report = report_summary(&findings, 0, 0);
    Ok(AnalysisBatchResponse {
        schema_version: ANALYSIS_BATCH_SCHEMA_VERSION,
        capabilities,
        cache_identity,
        findings,
        report,
    })
}
