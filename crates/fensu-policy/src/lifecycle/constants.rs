//! Public protocol and persistence schema versions.

pub const ANALYSIS_BATCH_SCHEMA_VERSION: u32 = 1;
pub const CACHE_SCHEMA_VERSION: u32 = 1;
pub const CUSTOM_HOST_PROTOCOL_VERSION: u32 = 1;
pub const SKILL_OWNERSHIP_SCHEMA_VERSION: u32 = 1;
pub(crate) const MATCH_ALL_PATH_PATTERN: &str = "**";
pub(crate) const SKILL_OWNER_PREFIX: &str = "<!-- fensu-policy-skill-owner: ";
pub(crate) const SKILL_OWNER_SUFFIX: &str = " -->";
