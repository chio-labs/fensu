//! Resolve applicable catalogue identities into deterministic policy tiers.

use crate::policy::_helpers::resolution;
use crate::policy::errors::PolicyError;
use crate::policy::main::validate_selector_group;
use crate::policy::models::{PolicyCatalogues, PolicySelection, PolicySelectors};
use crate::policy::types::{PolicyRule, RuleCodeGrammar};

/// Resolve metadata tiers while retaining aliases used for catalogue presentation.
pub fn resolve_catalogue_policy<'rules, Rule, Grammar>(
    catalogue: &[&'rules Rule],
    applicability: &Rule::Applicability,
    selectors: &PolicySelectors,
    grammar: &Grammar,
) -> Result<PolicySelection<'rules, Rule>, PolicyError>
where
    Rule: PolicyRule,
    Grammar: RuleCodeGrammar + ?Sized,
{
    let configured = catalogue.to_vec();
    let applicable = configured
        .iter()
        .copied()
        .filter(|rule| rule.is_applicable(applicability))
        .collect::<Vec<_>>();
    let catalogues = PolicyCatalogues {
        configured: &configured,
        applicable: &applicable,
    };
    for (group, group_selectors) in [
        ("select", &selectors.select),
        ("warn", &selectors.warn),
        ("ignore", &selectors.ignore),
    ] {
        validate_selector_group::validate_selector_group(
            group,
            group_selectors,
            &catalogues,
            grammar,
        )?;
    }
    let tiers = resolution::resolved_tiers(&applicable, selectors, grammar)?;
    Ok(PolicySelection {
        catalogue: applicable,
        blocking: tiers.blocking,
        warnings: tiers.warnings,
        ignored: tiers.ignored,
    })
}
