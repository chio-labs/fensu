//! Expose the compiled rule catalogue.

use crate::models::RuleMetadata;

pub(crate) fn configured_rule_catalogue(rule_packs: &[String]) -> Vec<&'static RuleMetadata> {
    crate::catalogue::_helpers::loading::configured_rule_catalogue(rule_packs)
}
