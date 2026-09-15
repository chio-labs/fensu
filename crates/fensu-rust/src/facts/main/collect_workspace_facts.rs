//! Public entry point for versioned parser-independent Rust workspace facts.

use std::path::Path;

use crate::facts::models::RustWorkspaceFacts;
use crate::models::WorkspaceCrate;

/// Build one deterministic fact payload without exposing Cargo or syn types.
pub fn collect_workspace_facts(
    repository_root: &Path,
    workspace_crates: &[WorkspaceCrate],
) -> RustWorkspaceFacts {
    crate::facts::_helpers::collection::collect(repository_root, workspace_crates)
}
