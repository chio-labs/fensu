//! Stable TypeScript parser and cache identities.

/// Changes whenever serialized facts need cache invalidation.
pub const CACHE_CONTRACT_VERSION: &str = "typescript-backend-v11";
/// Changes whenever parsing or fact extraction semantics change.
pub const PARSER_CONTRACT_VERSION: &str = "typescript-backend-v11";
