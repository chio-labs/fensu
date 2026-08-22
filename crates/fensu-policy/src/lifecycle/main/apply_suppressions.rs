//! Apply exact stale-checked suppressions and deliberate path-scoped ignores.

use std::collections::HashSet;

use crate::lifecycle::_helpers::paths::{matches, validate_pattern, validate_repository_path};
use crate::lifecycle::errors::LifecycleError;
use crate::lifecycle::main::sorted_findings::sorted_findings;
use crate::lifecycle::models::{
    ApplySuppressionsRequest, ExactSuppression, Finding, ScopedIgnore, SuppressionResult,
};
use crate::policy::types::RuleCodeGrammar;

/// Apply exact suppressions first, then broader scoped ignores.
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
    validate_configuration(suppressions, scoped_ignores, grammar)?;
    let evaluated = evaluated_codes
        .iter()
        .map(String::as_str)
        .collect::<HashSet<_>>();
    let mut applied = HashSet::<(String, String, Option<String>)>::new();
    let mut retained: Vec<Finding> = Vec::new();
    for finding in findings {
        let matching = suppressions.iter().find(|suppression| {
            suppression.code == finding.code
                && suppression.path == finding.path
                && suppression
                    .symbol
                    .as_ref()
                    .is_none_or(|symbol| finding.symbol.as_ref() == Some(symbol))
        });
        if let Some(suppression) = matching {
            applied.insert((
                suppression.code.clone(),
                suppression.path.clone(),
                suppression.symbol.clone(),
            ));
        } else {
            retained.push(finding);
        }
    }
    for suppression in suppressions {
        let key = (
            suppression.code.clone(),
            suppression.path.clone(),
            suppression.symbol.clone(),
        );
        if evaluated.contains(suppression.code.as_str()) && !applied.contains(&key) {
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
        let ignored = finding_is_scoped_ignored(finding, scoped_ignores, grammar);
        scoped_count += usize::from(ignored);
        !ignored
    });
    Ok(SuppressionResult {
        findings: sorted_findings(&retained),
        applied_suppressions: applied.len(),
        applied_scoped_ignores: scoped_count,
    })
}

fn validate_configuration<Grammar: RuleCodeGrammar>(
    suppressions: &[ExactSuppression],
    scoped_ignores: &[ScopedIgnore],
    grammar: &Grammar,
) -> Result<(), LifecycleError> {
    let mut exact: HashSet<(String, String, Option<String>)> = HashSet::new();
    let mut locations: HashSet<(String, String)> = HashSet::new();
    let mut file_wide: HashSet<(String, String)> = HashSet::new();
    for suppression in suppressions {
        if !grammar.rule_code_is_exact(&suppression.code) {
            return Err(LifecycleError::InvalidRuleCode {
                code: suppression.code.clone(),
            });
        }
        validate_repository_path(&suppression.path)?;
        if suppression.reason.trim().is_empty() {
            return Err(LifecycleError::InvalidConfiguration {
                message: "suppression reason must be non-empty".to_owned(),
            });
        }
        let location = (suppression.code.clone(), suppression.path.clone());
        let overlaps = file_wide.contains(&location)
            || suppression.symbol.is_none() && locations.contains(&location);
        if overlaps {
            return Err(LifecycleError::InvalidConfiguration {
                message: format!(
                    "overlapping exact suppressions for {} at {}",
                    suppression.code, suppression.path
                ),
            });
        }
        let key = (
            suppression.code.clone(),
            suppression.path.clone(),
            suppression.symbol.clone(),
        );
        if !exact.insert(key) {
            return Err(LifecycleError::InvalidConfiguration {
                message: format!(
                    "duplicate exact suppression for {} at {}",
                    suppression.code, suppression.path
                ),
            });
        }
        let _ = locations.insert(location.clone());
        if suppression.symbol.is_none() {
            let _ = file_wide.insert(location);
        }
    }
    for ignore in scoped_ignores {
        if ignore.selectors.is_empty() || ignore.paths.is_empty() || ignore.reason.trim().is_empty()
        {
            return Err(LifecycleError::InvalidConfiguration {
                message: "scoped ignores require selectors, paths, and a non-empty reason"
                    .to_owned(),
            });
        }
        for selector in &ignore.selectors {
            if !grammar.rule_selector_is_valid(selector) {
                return Err(LifecycleError::InvalidRuleCode {
                    code: selector.clone(),
                });
            }
        }
        for pattern in &ignore.paths {
            validate_pattern(pattern)?;
        }
    }
    Ok(())
}

fn finding_is_scoped_ignored<Grammar: RuleCodeGrammar>(
    finding: &Finding,
    scoped_ignores: &[ScopedIgnore],
    grammar: &Grammar,
) -> bool {
    for ignore in scoped_ignores {
        let rule_matches = ignore
            .selectors
            .iter()
            .any(|selector| grammar.code_matches_selector(&finding.code, selector));
        let path_matches = ignore
            .paths
            .iter()
            .any(|pattern| matches(&finding.path, pattern));
        if rule_matches && path_matches {
            return true;
        }
    }
    false
}
