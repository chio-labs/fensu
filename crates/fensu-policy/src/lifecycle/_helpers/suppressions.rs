//! Prepared exact and scoped suppression matching.

use std::collections::{HashMap, HashSet};

use globset::{GlobSet, GlobSetBuilder};

use crate::lifecycle::_helpers::paths::{compile_pattern, validate_repository_path};
use crate::lifecycle::errors::LifecycleError;
use crate::lifecycle::models::{ExactSuppression, Finding, ScopedIgnore};
use crate::policy::types::RuleCodeGrammar;

#[derive(Default)]
struct ExactLocation {
    file_wide: Option<usize>,
    symbols: HashMap<String, usize>,
}

#[derive(Default)]
struct ExactIndex {
    codes: HashMap<String, HashMap<String, ExactLocation>>,
}

impl ExactIndex {
    fn insert(
        &mut self,
        index: usize,
        suppression: &ExactSuppression,
    ) -> Result<(), LifecycleError> {
        let location = self
            .codes
            .entry(suppression.code.clone())
            .or_default()
            .entry(suppression.path.clone())
            .or_default();
        let overlaps = location.file_wide.is_some()
            || suppression.symbol.is_none() && !location.symbols.is_empty();
        if overlaps {
            return Err(LifecycleError::InvalidConfiguration {
                message: format!(
                    "overlapping exact suppressions for {} at {}",
                    suppression.code, suppression.path
                ),
            });
        }
        if let Some(symbol) = &suppression.symbol {
            if location.symbols.insert(symbol.clone(), index).is_some() {
                return Err(LifecycleError::InvalidConfiguration {
                    message: format!(
                        "duplicate exact suppression for {} at {}",
                        suppression.code, suppression.path
                    ),
                });
            }
        } else {
            location.file_wide = Some(index);
        }
        Ok(())
    }

    fn matching_index(&self, finding: &Finding) -> Option<usize> {
        let location = self.codes.get(&finding.code)?.get(&finding.path)?;
        location.file_wide.or_else(|| {
            finding
                .symbol
                .as_ref()
                .and_then(|symbol| location.symbols.get(symbol).copied())
        })
    }
}

pub(crate) struct PreparedSuppressions {
    exact: ExactIndex,
    scoped_paths: Vec<GlobSet>,
    scoped_by_code: HashMap<String, Vec<usize>>,
}

pub(crate) struct SuppressionPreparation<'a, Grammar> {
    pub(crate) findings: &'a [Finding],
    pub(crate) evaluated_codes: &'a [String],
    pub(crate) suppressions: &'a [ExactSuppression],
    pub(crate) scoped_ignores: &'a [ScopedIgnore],
    pub(crate) grammar: &'a Grammar,
}

impl PreparedSuppressions {
    pub(crate) fn matching_exact_index(&self, finding: &Finding) -> Option<usize> {
        self.exact.matching_index(finding)
    }

    pub(crate) fn is_scoped_ignored(&self, finding: &Finding) -> bool {
        self.scoped_by_code
            .get(&finding.code)
            .is_some_and(|indices| {
                indices
                    .iter()
                    .any(|index| self.scoped_paths[*index].is_match(&finding.path))
            })
    }
}

pub(crate) fn prepare_suppressions<Grammar: RuleCodeGrammar>(
    request: SuppressionPreparation<'_, Grammar>,
) -> Result<PreparedSuppressions, LifecycleError> {
    let SuppressionPreparation {
        findings,
        evaluated_codes,
        suppressions,
        scoped_ignores,
        grammar,
    } = request;
    let finding_codes = collect_validated_finding_codes(findings, evaluated_codes, grammar)?;
    let mut exact = ExactIndex::default();
    for (index, suppression) in suppressions.iter().enumerate() {
        validate_exact_code(&suppression.code, grammar)?;
        validate_repository_path(&suppression.path)?;
        if suppression.reason.trim().is_empty() {
            return Err(LifecycleError::InvalidConfiguration {
                message: "suppression reason must be non-empty".to_owned(),
            });
        }
        exact.insert(index, suppression)?;
    }
    let mut scoped_paths = Vec::with_capacity(scoped_ignores.len());
    let mut scoped_by_code: HashMap<String, Vec<usize>> = HashMap::new();
    for (index, ignore) in scoped_ignores.iter().enumerate() {
        validate_scoped_ignore(ignore, grammar)?;
        scoped_paths.push(compile_paths(&ignore.paths)?);
        for code in &finding_codes {
            if ignore
                .selectors
                .iter()
                .any(|selector| grammar.code_matches_selector(code, selector))
            {
                scoped_by_code.entry(code.clone()).or_default().push(index);
            }
        }
    }
    Ok(PreparedSuppressions {
        exact,
        scoped_paths,
        scoped_by_code,
    })
}

fn collect_validated_finding_codes<Grammar: RuleCodeGrammar>(
    findings: &[Finding],
    evaluated_codes: &[String],
    grammar: &Grammar,
) -> Result<HashSet<String>, LifecycleError> {
    let mut finding_codes: HashSet<String> = HashSet::new();
    for finding in findings {
        validate_exact_code(&finding.code, grammar)?;
        validate_repository_path(&finding.path)?;
        let _ = finding_codes.insert(finding.code.clone());
    }
    for code in evaluated_codes {
        validate_exact_code(code, grammar)?;
    }
    Ok(finding_codes)
}

fn validate_scoped_ignore<Grammar: RuleCodeGrammar>(
    ignore: &ScopedIgnore,
    grammar: &Grammar,
) -> Result<(), LifecycleError> {
    if ignore.selectors.is_empty() || ignore.paths.is_empty() || ignore.reason.trim().is_empty() {
        return Err(LifecycleError::InvalidConfiguration {
            message: "scoped ignores require selectors, paths, and a non-empty reason".to_owned(),
        });
    }
    for selector in &ignore.selectors {
        if !grammar.rule_selector_is_valid(selector) {
            return Err(LifecycleError::InvalidRuleCode {
                code: selector.clone(),
            });
        }
    }
    Ok(())
}

fn compile_paths(patterns: &[String]) -> Result<GlobSet, LifecycleError> {
    let mut builder = GlobSetBuilder::new();
    for pattern in patterns {
        builder.add(compile_pattern(pattern)?);
    }
    builder
        .build()
        .map_err(|_| LifecycleError::InvalidPathPattern {
            pattern: patterns.join(", "),
        })
}

fn validate_exact_code<Grammar: RuleCodeGrammar>(
    code: &str,
    grammar: &Grammar,
) -> Result<(), LifecycleError> {
    if !grammar.rule_code_is_exact(code) {
        return Err(LifecycleError::InvalidRuleCode {
            code: code.to_owned(),
        });
    }
    Ok(())
}
