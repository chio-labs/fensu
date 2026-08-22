//! Deterministic policy tier mechanics.

use crate::policy::errors::PolicyError;
use crate::policy::main::code_matches_selector;
use crate::policy::models::{PolicySelectors, ResolvedTiers};
use crate::policy::types::{PolicyRule, PolicyTier, RuleCodeGrammar};

pub(crate) fn resolved_tiers<'rules, Rule, Grammar>(
    applicable: &[&'rules Rule],
    selectors: &PolicySelectors,
    grammar: &Grammar,
) -> Result<ResolvedTiers<'rules, Rule>, PolicyError>
where
    Rule: PolicyRule,
    Grammar: RuleCodeGrammar + ?Sized,
{
    let ignored = matching_rules(applicable, &selectors.ignore, false, grammar);
    let mut blocking = matching_rules(applicable, &selectors.select, true, grammar);
    blocking.retain(|rule| !contains_code(&ignored, rule.code()));
    let warnings = matching_rules(applicable, &selectors.warn, true, grammar);
    validate_tier_overlap(&blocking, &warnings, &ignored)?;
    Ok(ResolvedTiers {
        blocking,
        warnings,
        ignored,
    })
}

fn matching_rules<'rules, Rule, Grammar>(
    catalogue: &[&'rules Rule],
    selectors: &[String],
    respect_default: bool,
    grammar: &Grammar,
) -> Vec<&'rules Rule>
where
    Rule: PolicyRule,
    Grammar: RuleCodeGrammar + ?Sized,
{
    let mut rules: Vec<&Rule> = Vec::new();
    for rule in catalogue {
        let mut matching = false;
        let mut exact = false;
        for selector in selectors {
            matching |=
                code_matches_selector::code_matches_selector(grammar, rule.code(), selector);
            exact |= selector == rule.code();
        }
        if matching && (!respect_default || rule.enabled_by_default() || exact) {
            rules.push(*rule);
        }
    }
    rules
}

fn validate_tier_overlap<Rule>(
    blocking: &[&Rule],
    warnings: &[&Rule],
    ignored: &[&Rule],
) -> Result<(), PolicyError>
where
    Rule: PolicyRule,
{
    for rule in blocking {
        if contains_code(warnings, rule.code()) {
            return Err(tier_conflict(
                rule.code(),
                PolicyTier::Blocking,
                PolicyTier::Warning,
            ));
        }
    }
    for rule in warnings {
        if contains_code(ignored, rule.code()) {
            return Err(tier_conflict(
                rule.code(),
                PolicyTier::Warning,
                PolicyTier::Ignored,
            ));
        }
    }
    Ok(())
}

fn contains_code<Rule>(rules: &[&Rule], code: &str) -> bool
where
    Rule: PolicyRule,
{
    rules.iter().any(|rule| rule.code() == code)
}

fn tier_conflict(code: &str, first: PolicyTier, second: PolicyTier) -> PolicyError {
    PolicyError::TierConflict {
        code: code.to_owned(),
        first,
        second,
    }
}
