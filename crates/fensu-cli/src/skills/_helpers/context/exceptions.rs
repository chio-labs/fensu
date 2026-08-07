use std::collections::HashSet;

use crate::catalogue::models::RuleMetadata;
use crate::models::Config;

pub(crate) fn validate(config: &Config, catalogue: &[RuleMetadata]) -> Result<(), String> {
    let codes = catalogue
        .iter()
        .map(|item| item.code.as_str())
        .collect::<HashSet<_>>();
    for exception in &config.exceptions {
        if !codes.contains(exception.rule.as_str()) {
            return Err(format!("Unknown rule exception code: {}.", exception.rule));
        }
    }
    Ok(())
}
