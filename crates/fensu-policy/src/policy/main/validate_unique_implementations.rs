//! Reject multiple display identities for one implementation.

use std::collections::BTreeMap;

use crate::policy::errors::PolicyError;
use crate::policy::types::PolicyRule;

/// Validate that selected rules map one-to-one to implementation identities.
pub fn validate_unique_implementations<Rule>(rules: &[&Rule]) -> Result<(), PolicyError>
where
    Rule: PolicyRule,
{
    let mut display_codes: BTreeMap<&str, &str> = BTreeMap::new();
    for rule in rules {
        if let Some(first_code) = display_codes.insert(rule.implementation_code(), rule.code()) {
            return Err(PolicyError::DuplicateImplementation {
                first_code: first_code.to_owned(),
                second_code: rule.code().to_owned(),
                implementation_code: rule.implementation_code().to_owned(),
            });
        }
    }
    Ok(())
}
