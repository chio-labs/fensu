//! Check generated skill ownership and content freshness.

use crate::lifecycle::_helpers::canonical;
use crate::lifecycle::_helpers::skills::{marker, parse_marker, replace_last};
use crate::lifecycle::constants::SKILL_OWNERSHIP_SCHEMA_VERSION;
use crate::lifecycle::models::SkillFreshness;

/// Compare installed generated content with its current owner and inputs.
pub fn skill_freshness(
    content: Option<&[u8]>,
    identity: &str,
    input_fingerprint: &str,
) -> SkillFreshness {
    let Some(content) = content else {
        return SkillFreshness::Missing;
    };
    let Some((ownership, final_marker)) = parse_marker(content) else {
        return SkillFreshness::Malformed;
    };
    if ownership.schema != SKILL_OWNERSHIP_SCHEMA_VERSION {
        return SkillFreshness::Malformed;
    }
    if ownership.identity != identity || ownership.input_fingerprint != input_fingerprint {
        return SkillFreshness::Stale;
    }
    let mut provisional = ownership.clone();
    provisional.content_fingerprint.clear();
    let provisional_marker = match marker(&provisional) {
        Ok(value) => value,
        Err(_) => return SkillFreshness::Malformed,
    };
    let provisional_content = match replace_last(
        content,
        final_marker.as_bytes(),
        provisional_marker.as_bytes(),
    ) {
        Some(value) => value,
        None => return SkillFreshness::Malformed,
    };
    match canonical::fingerprint(&provisional_content) {
        Ok(value) if value == ownership.content_fingerprint => SkillFreshness::Fresh,
        Ok(_) => SkillFreshness::Divergent,
        Err(_) => SkillFreshness::Malformed,
    }
}
