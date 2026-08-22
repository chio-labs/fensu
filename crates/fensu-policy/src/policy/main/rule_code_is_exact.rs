//! Validate one exact rule identity.

use crate::policy::_helpers::grammar;
use crate::policy::constants;

/// Return whether a value is one exact core, pack, or custom rule code.
pub fn rule_code_is_exact(value: &str) -> bool {
    let bytes = value.as_bytes();
    (bytes.len() == constants::CORE_RULE_CODE_LENGTH
        && value.starts_with(grammar::CORE_PREFIX)
        && bytes[2].is_ascii_uppercase()
        && bytes[3..].iter().all(u8::is_ascii_digit))
        || grammar::named_code_is_exact(value, grammar::PACK_PREFIX, true)
        || grammar::named_code_is_exact(value, grammar::CUSTOM_PREFIX, false)
}
