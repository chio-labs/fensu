//! Read compact task, knowledge, archive, and index counts.

use std::path::Path;

use crate::engine::errors::MemoryIndexError;
use crate::engine::helpers::querying::overviews;
use crate::engine::models::MemoryOverview;

/// Return a read-only overview from one synchronized memory index.
pub fn memory_overview(database_path: &Path) -> Result<MemoryOverview, MemoryIndexError> {
    overviews::read(database_path)
}
