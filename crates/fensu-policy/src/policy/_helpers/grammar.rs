//! Shared ASCII grammar primitives.

pub(crate) const CORE_PREFIX: &str = "FF";
pub(crate) const CUSTOM_PREFIX: &str = "X";
pub(crate) const PACK_PREFIX: &str = "FP";

pub(crate) fn named_code_is_exact(value: &str, prefix: &str, require_letters: bool) -> bool {
    value.strip_prefix(prefix).is_some_and(|suffix| {
        let first_digit = suffix
            .bytes()
            .position(|character| character.is_ascii_digit());
        first_digit.is_some_and(|index| {
            (!require_letters || index > 0)
                && suffix[..index]
                    .bytes()
                    .all(|character| character.is_ascii_uppercase())
                && suffix[index..]
                    .bytes()
                    .all(|character| character.is_ascii_digit())
        })
    })
}

pub(crate) fn named_selector_suffix_is_valid(suffix: &str) -> bool {
    let first_digit = suffix
        .bytes()
        .position(|character| character.is_ascii_digit())
        .unwrap_or(suffix.len());
    suffix[..first_digit]
        .bytes()
        .all(|character| character.is_ascii_uppercase())
        && suffix[first_digit..]
            .bytes()
            .all(|character| character.is_ascii_digit())
}
