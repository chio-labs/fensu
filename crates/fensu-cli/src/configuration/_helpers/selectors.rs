const CORE_PREFIX: &str = "FF";
const WEB_PREFIX: &str = "FW";
const CORE_RULE_CODE_LENGTH: usize = 6;
const CUSTOM_PREFIX: &str = "X";
const MAX_CORE_SELECTOR_SUFFIX: usize = 4;
const PACK_PREFIX: &str = "FP";

pub(crate) fn valid_code(value: &str) -> bool {
    let bytes = value.as_bytes();
    (bytes.len() == CORE_RULE_CODE_LENGTH
        && (value.starts_with(CORE_PREFIX) || value.starts_with(WEB_PREFIX))
        && bytes[2].is_ascii_uppercase()
        && bytes[3..].iter().all(u8::is_ascii_digit))
        || valid_named_code(value, PACK_PREFIX, true)
        || valid_named_code(value, CUSTOM_PREFIX, false)
}

pub(crate) fn valid_selector(value: &str) -> bool {
    if matches!(
        value,
        CORE_PREFIX | WEB_PREFIX | PACK_PREFIX | CUSTOM_PREFIX
    ) {
        return true;
    }
    if let Some(rest) = value
        .strip_prefix(CORE_PREFIX)
        .or_else(|| value.strip_prefix(WEB_PREFIX))
    {
        return rest.len() <= MAX_CORE_SELECTOR_SUFFIX
            && rest
                .chars()
                .next()
                .is_some_and(|item| item.is_ascii_uppercase())
            && rest[1..].chars().all(|item| item.is_ascii_digit());
    }
    if let Some(rest) = value.strip_prefix(PACK_PREFIX) {
        return !rest.is_empty() && named_selector_suffix_is_valid(rest);
    }
    value
        .strip_prefix(CUSTOM_PREFIX)
        .is_some_and(named_selector_suffix_is_valid)
}

fn valid_named_code(value: &str, prefix: &str, require_namespace: bool) -> bool {
    value.strip_prefix(prefix).is_some_and(|rest| {
        let digit = rest.find(|character: char| character.is_ascii_digit());
        digit.is_some_and(|index| {
            rest[..index]
                .chars()
                .all(|character| character.is_ascii_uppercase())
                && (!require_namespace || index > 0)
                && !rest[index..].is_empty()
                && rest[index..]
                    .chars()
                    .all(|character| character.is_ascii_digit())
        })
    })
}

fn named_selector_suffix_is_valid(rest: &str) -> bool {
    let digit = rest
        .find(|character: char| character.is_ascii_digit())
        .unwrap_or(rest.len());
    rest[..digit].chars().all(|item| item.is_ascii_uppercase())
        && rest[digit..].chars().all(|item| item.is_ascii_digit())
}
