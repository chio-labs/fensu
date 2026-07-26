//! Look one rule up in the compiled catalogue.

use crate::models::RuleMetadata;

pub(crate) fn rule_metadata(code: &str) -> Option<&'static RuleMetadata> {
    crate::catalogue::_helpers::loading::rule_metadata(code)
}
