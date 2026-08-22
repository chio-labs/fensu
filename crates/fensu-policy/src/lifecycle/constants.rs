//! Public protocol and persistence schema versions.

pub const ANALYSIS_BATCH_SCHEMA_VERSION: u32 = 1;
pub const CACHE_IDENTITY_SCHEMA_VERSION: u32 = 2;
pub const CACHE_SCHEMA_VERSION: u32 = 1;
pub const CUSTOM_HOST_PROTOCOL_VERSION: u32 = 1;
pub const SKILL_OWNERSHIP_SCHEMA_VERSION: u32 = 2;
pub(crate) const LEGACY_SKILL_OWNERSHIP_SCHEMA_VERSION: u32 = 1;
pub(crate) const CUSTOM_HOST_CLEANUP_MILLIS: u64 = 2_000;
pub(crate) const MATCH_ALL_PATH_PATTERN: &str = "**";
pub(crate) const CURRENT_PATH_SEGMENT: &str = ".";
pub(crate) const PARENT_PATH_SEGMENT: &str = "..";
pub(crate) const SKILL_OWNER_PREFIX: &str = "<!-- fensu-policy-skill-owner: ";
pub(crate) const SKILL_OWNER_SUFFIX: &str = " -->";
