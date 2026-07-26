use std::path::Path;

use crate::configuration::_helpers::loading;

pub(crate) fn custom_rules_are_configured(start: &Path) -> Result<bool, String> {
    loading::custom_rules_are_configured(start)
}
