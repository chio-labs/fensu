//! Primitive semantic validation for native cache payload values.

use std::collections::HashSet;
use std::path::{Component, Path};

use crate::cache::constants::{
    CORE_RULE_SUFFIX_LENGTH, DEPENDENCY_GLOB_KIND, FINGERPRINT_LENGTH, MAXIMUM_SYMBOL_PARTS,
    REPOSITORY_ROOT_PATH,
};
use crate::cache::models::{CanonicalValue, NativeDependencyObservation};

pub(crate) fn valid_fingerprint(value: &str) -> bool {
    value.len() == FINGERPRINT_LENGTH
        && value
            .bytes()
            .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
}

pub(crate) fn valid_relative_path(value: &str, allow_root: bool) -> bool {
    if value == REPOSITORY_ROOT_PATH {
        return allow_root;
    }
    !value.is_empty()
        && !value.contains('\\')
        && !Path::new(value).is_absolute()
        && Path::new(value)
            .components()
            .all(|component| matches!(component, Component::Normal(_)))
}

pub(crate) fn valid_dependency_shape(observation: &NativeDependencyObservation) -> bool {
    let key = &observation.key;
    if key.kind == DEPENDENCY_GLOB_KIND {
        if key.pattern.as_ref().is_none_or(String::is_empty) {
            return false;
        }
    } else if key.pattern.is_some() || key.recursive {
        return false;
    }
    match key.kind.as_str() {
        "source" => {
            observation.answer.is_null()
                || observation.answer.as_str().is_some_and(valid_fingerprint)
        }
        "exists" | "is_file" | "is_dir" => observation.answer.as_bool().is_some(),
        "directory_entries" | DEPENDENCY_GLOB_KIND | "python_anchor" => {
            observation.answer.as_list().is_some_and(|items| {
                items.iter().all(|item| {
                    item.as_str()
                        .is_some_and(|path| valid_relative_path(path, true))
                })
            })
        }
        _ => false,
    }
}

pub(crate) fn valid_contribution(value: &CanonicalValue) -> Option<&str> {
    if !exact_fields(
        value,
        &[
            "applied_exception_keys",
            "faults",
            "path",
            "threshold_override_uses",
            "warnings",
        ],
    ) {
        return None;
    }
    let path = value.field("path")?.as_str()?;
    valid_relative_path(path, false).then_some(())?;
    let faults = value.field("faults")?.as_list()?;
    let warnings = value.field("warnings")?.as_list()?;
    let exceptions = value.field("applied_exception_keys")?.as_list()?;
    let uses = value.field("threshold_override_uses")?.as_list()?;
    if faults.is_empty() && warnings.is_empty() && exceptions.is_empty() && uses.is_empty() {
        return None;
    }
    decode_faults(value.field("faults")?, path)?;
    decode_faults(value.field("warnings")?, path)?;
    decode_exceptions(value.field("applied_exception_keys")?, path)?;
    decode_threshold_uses(value.field("threshold_override_uses")?)?;
    Some(path)
}

pub(crate) fn decode_faults(value: &CanonicalValue, owner: &str) -> Option<()> {
    for fault in value.as_list()? {
        if !exact_fields(
            fault,
            &["code", "column", "line", "message", "path", "remediation"],
        ) || !valid_rule_code(fault.field("code")?.as_str()?)
            || fault.field("path")?.as_str()? != owner
            || fault.field("message")?.as_str().is_none()
            || !optional_position(fault.field("line")?, 1)
            || !optional_position(fault.field("column")?, 0)
            || fault.field("line")?.is_null() && !fault.field("column")?.is_null()
            || optional_string(fault.field("remediation")?).is_none()
        {
            return None;
        }
    }
    Some(())
}

pub(crate) fn decode_exceptions(value: &CanonicalValue, owner: &str) -> Option<()> {
    let mut previous: Option<(String, String, String)> = None;
    for key in value.as_list()? {
        if !exact_fields(key, &["path", "rule", "symbol"])
            || key.field("path")?.as_str()? != owner
            || !valid_rule_code(key.field("rule")?.as_str()?)
        {
            return None;
        }
        let symbol = optional_string(key.field("symbol")?)?;
        if symbol.as_ref().is_some_and(|value| !valid_symbol(value)) {
            return None;
        }
        let identity = (
            key.field("rule")?.as_str()?.to_owned(),
            owner.to_owned(),
            symbol.unwrap_or_default(),
        );
        if previous.as_ref().is_some_and(|prior| prior >= &identity) {
            return None;
        }
        previous = Some(identity);
    }
    Some(())
}

pub(crate) fn decode_threshold_uses(value: &CanonicalValue) -> Option<()> {
    let mut identities = HashSet::new();
    for item in value.as_list()? {
        if !exact_fields(
            item,
            &[
                "effective_value",
                "matched_pattern",
                "override_order",
                "reason",
                "repository_path",
                "threshold",
            ],
        ) || item.field("threshold")?.as_str()?.is_empty()
            || item.field("matched_pattern")?.as_str()?.is_empty()
            || item.field("reason")?.as_str()?.trim().is_empty()
            || !valid_relative_path(item.field("repository_path")?.as_str()?, false)
            || item
                .field("effective_value")?
                .as_nonnegative_i64()
                .is_none()
            || item.field("override_order")?.as_nonnegative_i64().is_none()
            || !identities.insert(format!("{item:?}"))
        {
            return None;
        }
    }
    Some(())
}

pub(crate) fn exact_fields(value: &CanonicalValue, expected: &[&str]) -> bool {
    let Some(entries) = value.as_object() else {
        return false;
    };
    entries.len() == expected.len()
        && expected
            .iter()
            .all(|name| entries.iter().any(|(key, _)| key == name))
}

pub(crate) fn optional_fingerprint(value: &CanonicalValue) -> Option<Option<String>> {
    if value.is_null() {
        return Some(None);
    }
    let value = value.as_str()?;
    valid_fingerprint(value).then(|| Some(value.to_owned()))
}

pub(crate) fn optional_string(value: &CanonicalValue) -> Option<Option<String>> {
    if value.is_null() {
        Some(None)
    } else {
        value.as_str().map(|value| Some(value.to_owned()))
    }
}

fn optional_position(value: &CanonicalValue, minimum: i64) -> bool {
    value.is_null()
        || value
            .as_nonnegative_i64()
            .is_some_and(|value| value >= minimum)
}

fn valid_rule_code(value: &str) -> bool {
    if let Some(suffix) = value.strip_prefix("SF") {
        return suffix.len() == CORE_RULE_SUFFIX_LENGTH
            && suffix.as_bytes()[0].is_ascii_uppercase()
            && suffix.as_bytes()[1..].iter().all(u8::is_ascii_digit);
    }
    let Some(suffix) = value.strip_prefix('X') else {
        return false;
    };
    let letters = suffix.bytes().take_while(u8::is_ascii_uppercase).count();
    !suffix[letters..].is_empty() && suffix[letters..].bytes().all(|byte| byte.is_ascii_digit())
}

fn valid_symbol(value: &str) -> bool {
    let parts = value.split('.').collect::<Vec<_>>();
    (1..=MAXIMUM_SYMBOL_PARTS).contains(&parts.len())
        && parts.iter().all(|part| {
            let mut bytes = part.bytes();
            bytes
                .next()
                .is_some_and(|byte| byte == b'_' || byte.is_ascii_alphabetic())
                && bytes.all(|byte| byte == b'_' || byte.is_ascii_alphanumeric())
        })
}
