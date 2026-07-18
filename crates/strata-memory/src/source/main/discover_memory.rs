//! Discover canonical memory sources without writing repository state.

use std::path::Path;

use crate::source::helpers::discovery;
use crate::source::models::DiscoveryResult;

/// Return all canonical sources and recoverable diagnostics under `.ai`.
pub fn discover_memory(repository_root: &Path) -> DiscoveryResult {
    discovery::collect_memory_sources(repository_root)
}
