//! Validate canonical memory directly and publish only a valid loaded corpus.

use std::path::Path;

use crate::engine::errors::MemoryIndexError;
use crate::engine::helpers::publication::database;
use crate::engine::models::MemoryCheckResult;
use crate::source::main::discover_memory::discover_memory;

/// Return direct-source findings and publish the already-loaded valid corpus.
pub fn check_memory(
    repository_root: &Path,
    database_path: &Path,
) -> Result<MemoryCheckResult, MemoryIndexError> {
    let discovery = discover_memory(repository_root);
    let result = database::publish_discovery(discovery, database_path, true)?;
    let published = result.published.then_some(result.summary);
    Ok(MemoryCheckResult {
        diagnostics: result.diagnostics,
        published,
    })
}
