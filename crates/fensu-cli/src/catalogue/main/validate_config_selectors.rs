//! Validate configured selectors against the activated rule catalogue.

use crate::catalogue::models::RuleMetadata;
use crate::models::Config;

pub(crate) fn validate_config_selectors(
    config: &Config,
    catalogue: &[&RuleMetadata],
) -> Result<(), String> {
    for (name, selectors) in [
        ("select", &config.select),
        ("warn", &config.warn),
        ("ignore", &config.ignore),
    ] {
        validate_selector_group(name, selectors, catalogue)?;
    }
    for entry in &config.rule_ignores {
        validate_selector_group("rule_ignores.rules", &entry.rules, catalogue)?;
    }
    Ok(())
}

fn validate_selector_group(
    name: &str,
    selectors: &[String],
    catalogue: &[&RuleMetadata],
) -> Result<(), String> {
    for selector in selectors {
        if catalogue.iter().any(|rule| rule.code.starts_with(selector)) {
            continue;
        }
        return Err(format!(
            "Config key {name} contains selector {selector}, but it matches no rules in the configured catalogue. Activate the required rule pack, or correct or remove the selector."
        ));
    }
    Ok(())
}
