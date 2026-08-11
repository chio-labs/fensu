//! Validate configured selectors against the activated rule catalogue.

use crate::catalogue::models::{RuleMetadata, SelectorCatalogues};
use crate::configuration::main::is_rule_code::is_rule_code;
use crate::models::Config;

pub(crate) fn validate_config_selectors(
    config: &Config,
    catalogue: &[&RuleMetadata],
    configured_catalogue: &[&RuleMetadata],
) -> Result<(), String> {
    let catalogues = SelectorCatalogues {
        applicable: catalogue,
        configured: configured_catalogue,
    };
    for (name, selectors) in [
        ("select", &config.select),
        ("warn", &config.warn),
        ("ignore", &config.ignore),
    ] {
        validate_selector_group(name, selectors, &catalogues, config)?;
    }
    for entry in &config.rule_ignores {
        validate_selector_group("rule_ignores.rules", &entry.rules, &catalogues, config)?;
    }
    Ok(())
}

fn validate_selector_group(
    name: &str,
    selectors: &[String],
    catalogues: &SelectorCatalogues<'_>,
    config: &Config,
) -> Result<(), String> {
    for selector in selectors {
        if catalogues
            .applicable
            .iter()
            .any(|rule| rule.code.starts_with(selector))
        {
            continue;
        }
        if catalogues
            .configured
            .iter()
            .any(|rule| rule.code.starts_with(selector))
        {
            let selection = if is_rule_code(selector) {
                format!("selects rule {selector}")
            } else {
                format!("contains selector {selector}")
            };
            return Err(format!(
                "Config key {name} {selection}, but matching rules are not applicable to analyzer {}.",
                config.analyzer
            ));
        }
        return Err(format!(
            "Config key {name} contains selector {selector}, but it matches no rules in the configured catalogue. Activate the required rule pack, or correct or remove the selector."
        ));
    }
    Ok(())
}
