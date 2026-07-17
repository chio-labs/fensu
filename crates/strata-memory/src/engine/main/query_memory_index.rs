//! Run one bounded read-only query against a published memory index.

use std::path::Path;

use crate::engine::errors::MemoryIndexError;
use crate::engine::helpers::querying::queries;
use crate::engine::models::MemoryQueryResult;

/// Return bounded rows from one caller-supplied read-only DuckDB query.
pub fn query_memory_index(
    database_path: &Path,
    sql: &str,
    limit: usize,
) -> Result<MemoryQueryResult, MemoryIndexError> {
    queries::run(database_path, sql, limit)
}
