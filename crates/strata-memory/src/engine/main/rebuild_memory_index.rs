//! Rebuild and atomically publish one repository memory index.

use std::path::Path;

use crate::engine::errors::MemoryIndexError;
use crate::engine::helpers::publication::database;
use crate::engine::models::IndexSummary;
use crate::source::main::discover_memory::discover_memory;

/// Load the complete corpus and atomically replace its SQLite index.
pub fn rebuild_memory_index(
    repository_root: &Path,
    database_path: &Path,
) -> Result<IndexSummary, MemoryIndexError> {
    let discovery = discover_memory(repository_root);
    database::publish_discovery(discovery, database_path, false).map(|result| result.summary)
}
