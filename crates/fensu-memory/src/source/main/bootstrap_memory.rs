//! Safely create canonical source directories for enabled repository memory.

use std::path::Path;

use crate::source::helpers::bootstrap;

/// Validate existing sources and create missing canonical memory state once.
pub fn bootstrap_memory(repository_root: &Path) -> Result<(), String> {
    bootstrap::bootstrap(repository_root)
}
