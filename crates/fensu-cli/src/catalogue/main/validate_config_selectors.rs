//! Validate configured selectors against the activated rule catalogue.

use fensu_policy::policy::errors::PolicyError;
use fensu_policy::policy::main::validate_selector_group;
use fensu_policy::policy::models::{FensuRuleCodeGrammar, PolicyCatalogues};

use crate::catalogue::models::{RuleMetadata, SelectorValidationRequest};
use crate::models::Config;

pub(crate) fn validate_config_selectors(
    config: &Config,
    catalogue: &[&RuleMetadata],
    configured_catalogue: &[&RuleMetadata],
) -> Result<(), String> {
    for (name, selectors) in [
        ("select", &config.select),
        ("warn", &config.warn),
        ("ignore", &config.ignore),
    ] {
        validate_group(SelectorValidationRequest {
            name,
            selectors,
            applicable: catalogue,
            configured: configured_catalogue,
            analyzer: &config.analyzer,
        })?;
    }
    for entry in &config.rule_ignores {
        validate_group(SelectorValidationRequest {
            name: "rule_ignores.rules",
            selectors: &entry.rules,
            applicable: catalogue,
            configured: configured_catalogue,
            analyzer: &config.analyzer,
        })?;
    }
    Ok(())
}

fn validate_group(request: SelectorValidationRequest<'_>) -> Result<(), String> {
    let catalogues = PolicyCatalogues {
        configured: request.configured,
        applicable: request.applicable,
    };
    validate_selector_group::validate_selector_group(
        request.name,
        request.selectors,
        &catalogues,
        &FensuRuleCodeGrammar,
    )
        .map_err(|error| match error {
            PolicyError::InvalidSelector { group, selector } => {
                format!("Config key {group} contains invalid selector {selector}.")
            }
            PolicyError::SelectorMatchesOnlyInapplicableRules {
                group,
                selector,
                exact,
            } => {
                let selection = if exact {
                format!("selects rule {selector}")
            } else {
                format!("contains selector {selector}")
            };
                format!(
                    "Config key {group} {selection}, but matching rules are not applicable to analyzer {}.",
                    request.analyzer
                )
            }
            PolicyError::SelectorMatchesNoConfiguredRule { group, selector } => format!(
                "Config key {group} contains selector {selector}, but it matches no rules in the configured catalogue. Activate the required rule pack, or correct or remove the selector."
            ),
            other => format!("Unexpected selector validation failure: {other}"),
        })
}
