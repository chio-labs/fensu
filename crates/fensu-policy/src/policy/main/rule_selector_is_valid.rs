//! Validate one exact or prefix rule selector.

use crate::policy::_helpers::grammar;
use crate::policy::constants;

/// Return whether a value is a syntactically valid rule selector.
pub fn rule_selector_is_valid(value: &str) -> bool {
    if matches!(
        value,
        grammar::CORE_PREFIX | grammar::PACK_PREFIX | grammar::CUSTOM_PREFIX
    ) {
        return true;
    }
    if let Some(suffix) = value.strip_prefix(grammar::CORE_PREFIX) {
        return suffix.len() <= constants::MAX_CORE_SELECTOR_SUFFIX
            && suffix
                .bytes()
                .next()
                .is_some_and(|character| character.is_ascii_uppercase())
            && suffix[1..]
                .bytes()
                .all(|character| character.is_ascii_digit());
    }
    if let Some(suffix) = value.strip_prefix(grammar::PACK_PREFIX) {
        return !suffix.is_empty() && grammar::named_selector_suffix_is_valid(suffix);
    }
    value
        .strip_prefix(grammar::CUSTOM_PREFIX)
        .is_some_and(grammar::named_selector_suffix_is_valid)
}
