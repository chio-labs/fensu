//! Expose the compiled rule catalogue.

use crate::catalogue::models::RuleMetadata;

pub(crate) fn configured_rule_catalogue(
    rule_packs: &[String],
) -> Result<Vec<&'static RuleMetadata>, String> {
    crate::catalogue::_helpers::loading::configured_rule_catalogue(rule_packs)
}
