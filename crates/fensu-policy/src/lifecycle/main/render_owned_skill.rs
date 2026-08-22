//! Attach deterministic ownership to generated skill content.

use crate::lifecycle::_helpers::canonical;
use crate::lifecycle::_helpers::skills::{
    append_marker, marker, owner_marker_present, replace_last,
};
use crate::lifecycle::constants::SKILL_OWNERSHIP_SCHEMA_VERSION;
use crate::lifecycle::errors::LifecycleError;
use crate::lifecycle::models::SkillOwnership;

/// Attach one deterministic ownership marker to generated skill content.
pub fn render_owned_skill(
    identity: &str,
    input_fingerprint: &str,
    content: &[u8],
) -> Result<Vec<u8>, LifecycleError> {
    if owner_marker_present(content) {
        return Err(LifecycleError::InvalidConfiguration {
            message: "generated skill content already contains an ownership marker".to_owned(),
        });
    }
    let mut ownership = SkillOwnership {
        schema: SKILL_OWNERSHIP_SCHEMA_VERSION,
        identity: identity.to_owned(),
        input_fingerprint: input_fingerprint.to_owned(),
        content_fingerprint: String::new(),
    };
    let provisional_marker = marker(&ownership)?;
    let provisional = append_marker(content, &provisional_marker);
    ownership.content_fingerprint = canonical::fingerprint(&provisional)?;
    let final_marker = marker(&ownership)?;
    replace_last(
        &provisional,
        provisional_marker.as_bytes(),
        final_marker.as_bytes(),
    )
    .ok_or_else(|| LifecycleError::Serialization {
        message: "could not replace provisional skill ownership marker".to_owned(),
    })
}
