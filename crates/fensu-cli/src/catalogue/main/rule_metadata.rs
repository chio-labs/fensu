//! Look one rule up in the compiled catalogue.

use crate::catalogue::models::RuleMetadata;

pub(crate) fn rule_metadata(code: &str) -> Result<Option<&'static RuleMetadata>, String> {
    crate::catalogue::_helpers::loading::rule_metadata(code)
}
