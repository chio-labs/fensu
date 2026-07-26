//! Expose the compiled rule catalogue.

use crate::models::RuleMetadata;

pub(crate) fn rule_catalogue() -> &'static [RuleMetadata] {
    crate::catalogue::_helpers::loading::rule_catalogue()
}
