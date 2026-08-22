//! Apply exact stale-checked suppressions and deliberate path-scoped ignores.

use std::collections::HashSet;

use crate::lifecycle::_helpers::suppressions::{prepare_suppressions, SuppressionPreparation};
use crate::lifecycle::errors::LifecycleError;
use crate::lifecycle::main::sorted_findings::sorted_findings;
use crate::lifecycle::models::{ApplySuppressionsRequest, Finding, SuppressionResult};
use crate::policy::types::RuleCodeGrammar;

/// Apply indexed exact suppressions first, then precompiled scoped ignores.
pub fn apply_suppressions<Grammar: RuleCodeGrammar>(
    request: ApplySuppressionsRequest<'_, Grammar>,
) -> Result<SuppressionResult, LifecycleError> {
    let ApplySuppressionsRequest {
        findings,
        evaluated_codes,
        suppressions,
        scoped_ignores,
        grammar,
    } = request;
    let prepared = prepare_suppressions(SuppressionPreparation {
        findings: &findings,
        evaluated_codes,
        suppressions,
        scoped_ignores,
        grammar,
    })?;
    let evaluated = evaluated_codes
        .iter()
        .map(String::as_str)
        .collect::<HashSet<_>>();
    let mut applied: HashSet<usize> = HashSet::new();
    let mut retained: Vec<Finding> = Vec::new();
    for finding in findings {
        if let Some(index) = prepared.matching_exact_index(&finding) {
            let _ = applied.insert(index);
        } else {
            retained.push(finding);
        }
    }
    for (index, suppression) in suppressions.iter().enumerate() {
        if evaluated.contains(suppression.code.as_str()) && !applied.contains(&index) {
            return Err(LifecycleError::StaleSuppression {
                code: suppression.code.clone(),
                path: suppression.path.clone(),
                symbol: suppression.symbol.clone(),
                reason: suppression.reason.clone(),
            });
        }
    }
    let mut scoped_count = 0;
    retained.retain(|finding| {
        let ignored = prepared.is_scoped_ignored(finding);
        scoped_count += usize::from(ignored);
        !ignored
    });
    Ok(SuppressionResult {
        findings: sorted_findings(&retained),
        applied_suppressions: applied.len(),
        applied_scoped_ignores: scoped_count,
    })
}
