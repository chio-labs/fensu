//! Resolve applicable rules into deterministic policy tiers.

use crate::policy::errors::PolicyError;
use crate::policy::main::resolve_catalogue_policy;
use crate::policy::main::validate_unique_implementations;
use crate::policy::models::{PolicySelection, PolicySelectors};
use crate::policy::types::{PolicyRule, RuleCodeGrammar};

/// Resolve configured rules for one consumer-owned applicability context.
pub fn resolve_policy<'rules, Rule, Grammar>(
    catalogue: &[&'rules Rule],
    applicability: &Rule::Applicability,
    selectors: &PolicySelectors,
    grammar: &Grammar,
) -> Result<PolicySelection<'rules, Rule>, PolicyError>
where
    Rule: PolicyRule,
    Grammar: RuleCodeGrammar + ?Sized,
{
    let selection = resolve_catalogue_policy::resolve_catalogue_policy(
        catalogue,
        applicability,
        selectors,
        grammar,
    )?;
    let active = selection
        .blocking
        .iter()
        .chain(&selection.warnings)
        .copied()
        .collect::<Vec<_>>();
    validate_unique_implementations::validate_unique_implementations(&active)?;
    Ok(selection)
}
