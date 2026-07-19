//! Reconcile canonical sources with one atomically published memory index.

use std::path::Path;

use crate::engine::errors::MemoryIndexError;
use crate::engine::helpers::reporting::synchronization;
use crate::engine::models::SyncSummary;
use crate::source::main::discover_memory::discover_memory;

/// Synchronize one repository without parsing or writing an unchanged corpus.
pub fn sync_memory_index(
    repository_root: &Path,
    database_path: &Path,
) -> Result<SyncSummary, MemoryIndexError> {
    let discovery = discover_memory(repository_root);
    synchronization::sync(discovery, database_path)
}
