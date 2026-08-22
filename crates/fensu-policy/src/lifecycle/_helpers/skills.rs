//! Skill ownership marker encoding and parsing.

use serde_json::json;

use crate::lifecycle::_helpers::canonical;
use crate::lifecycle::constants::{SKILL_OWNER_PREFIX, SKILL_OWNER_SUFFIX};
use crate::lifecycle::errors::LifecycleError;
use crate::lifecycle::models::SkillOwnership;

pub(crate) fn append_marker(content: &[u8], marker: &str) -> Vec<u8> {
    let mut output = content.to_vec();
    if !output.ends_with(b"\n") {
        output.push(b'\n');
    }
    output.extend_from_slice(marker.as_bytes());
    output.push(b'\n');
    output
}

pub(crate) fn marker(ownership: &SkillOwnership) -> Result<String, LifecycleError> {
    let value = json!({
        "content_fingerprint": ownership.content_fingerprint,
        "identity": ownership.identity,
        "input_fingerprint": ownership.input_fingerprint,
        "schema": ownership.schema,
    });
    let encoded = canonical::canonical_json(&value)?;
    let text = String::from_utf8(encoded).map_err(|error| LifecycleError::Serialization {
        message: error.to_string(),
    })?;
    Ok(format!("{SKILL_OWNER_PREFIX}{text}{SKILL_OWNER_SUFFIX}"))
}

pub(crate) fn parse_marker(content: &[u8]) -> Option<(SkillOwnership, String)> {
    let matches = content
        .split(|byte| *byte == b'\n')
        .map(|line| line.strip_suffix(b"\r").unwrap_or(line))
        .filter(|line| line.starts_with(SKILL_OWNER_PREFIX.as_bytes()))
        .collect::<Vec<_>>();
    let [line] = matches.as_slice() else {
        return None;
    };
    if !line.ends_with(SKILL_OWNER_SUFFIX.as_bytes()) {
        return None;
    }
    let raw = &line[SKILL_OWNER_PREFIX.len()..line.len() - SKILL_OWNER_SUFFIX.len()];
    let ownership = match serde_json::from_slice::<SkillOwnership>(raw) {
        Ok(value) => value,
        Err(_) => return None,
    };
    let text = match std::str::from_utf8(line) {
        Ok(value) => value.to_owned(),
        Err(_) => return None,
    };
    Some((ownership, text))
}

pub(crate) fn owner_marker_present(content: &[u8]) -> bool {
    content
        .split(|byte| *byte == b'\n')
        .map(|line| line.strip_suffix(b"\r").unwrap_or(line))
        .any(|line| line.starts_with(SKILL_OWNER_PREFIX.as_bytes()))
}

pub(crate) fn replace_last(content: &[u8], from: &[u8], to: &[u8]) -> Option<Vec<u8>> {
    let start = content
        .windows(from.len())
        .rposition(|window| window == from)?;
    let mut output = Vec::with_capacity(content.len() - from.len() + to.len());
    output.extend_from_slice(&content[..start]);
    output.extend_from_slice(to);
    output.extend_from_slice(&content[start + from.len()..]);
    Some(output)
}
