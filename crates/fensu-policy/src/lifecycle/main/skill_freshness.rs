//! Check generated skill ownership and content freshness.

use crate::lifecycle::_helpers::canonical;
use crate::lifecycle::_helpers::skills::{
    marker, parse_marker, replace_last, ParsedSkillOwnership,
};
use crate::lifecycle::models::SkillFreshness;

/// Compare generated content with its owner and inputs without claiming v1 or foreign files.
pub fn skill_freshness(
    content: Option<&[u8]>,
    owner: &str,
    identity: &str,
    input_fingerprint: &str,
) -> SkillFreshness {
    let Some(content) = content else {
        return SkillFreshness::Missing;
    };
    let Some((parsed, final_marker)) = parse_marker(content) else {
        return SkillFreshness::Malformed;
    };
    let ParsedSkillOwnership::Current(ownership) = parsed else {
        return SkillFreshness::Unowned;
    };
    if ownership.owner != owner {
        return SkillFreshness::Unowned;
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
        Ok(value) if value != ownership.content_fingerprint => SkillFreshness::Divergent,
        Ok(_)
            if ownership.identity != identity
                || ownership.input_fingerprint != input_fingerprint =>
        {
            SkillFreshness::Stale
        }
        Ok(_) => SkillFreshness::Fresh,
        Err(_) => SkillFreshness::Malformed,
    }
}
