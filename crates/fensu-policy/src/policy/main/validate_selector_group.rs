//! Validate selectors against configured and applicable catalogues.

use crate::policy::errors::PolicyError;
use crate::policy::main::code_matches_selector;
use crate::policy::models::PolicyCatalogues;
use crate::policy::types::{PolicyRule, RuleCodeGrammar};

/// Validate one named selector group with applicability-aware failures.
pub fn validate_selector_group<Rule, Grammar>(
    group: &str,
    selectors: &[String],
    catalogues: &PolicyCatalogues<'_, Rule>,
    grammar: &Grammar,
) -> Result<(), PolicyError>
where
    Rule: PolicyRule,
    Grammar: RuleCodeGrammar + ?Sized,
{
    for selector in selectors {
        if !grammar.rule_selector_is_valid(selector) {
            return Err(PolicyError::InvalidSelector {
                group: group.to_owned(),
                selector: selector.clone(),
            });
        }
        if catalogues.applicable.iter().any(|rule| {
            code_matches_selector::code_matches_selector(grammar, rule.code(), selector)
        }) {
            continue;
        }
        if catalogues.configured.iter().any(|rule| {
            code_matches_selector::code_matches_selector(grammar, rule.code(), selector)
        }) {
            return Err(PolicyError::SelectorMatchesOnlyInapplicableRules {
                group: group.to_owned(),
                selector: selector.clone(),
                exact: grammar.rule_code_is_exact(selector),
            });
        }
        return Err(PolicyError::SelectorMatchesNoConfiguredRule {
            group: group.to_owned(),
            selector: selector.clone(),
        });
    }
    Ok(())
}
