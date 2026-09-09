//! Stable Rust analyzer contract identities.

/// Changes whenever source interpretation can change for identical Rust bytes.
pub const PARSER_CONTRACT_VERSION: &str = "rust-syn-workspace-v1";

/// Changes whenever repository analysis or diagnostic behavior changes.
pub const CACHE_CONTRACT_VERSION: &str = "rust-structure-policy-v1";

/// Structure-engine implementation code used when Cargo metadata is unavailable.
pub const METADATA_SETUP_CODE: &str = "RSL901";
