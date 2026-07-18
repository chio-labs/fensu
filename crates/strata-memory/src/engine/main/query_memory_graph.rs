//! Run one bounded graph traversal against a published memory index.

use std::path::Path;

use crate::engine::errors::MemoryIndexError;
use crate::engine::helpers::querying::graphs;
use crate::engine::models::{MemoryGraphQuery, MemoryGraphResult};

/// Resolve roots and return one deterministic bounded graph.
pub fn query_memory_graph(
    database_path: &Path,
    query: &MemoryGraphQuery,
) -> Result<MemoryGraphResult, MemoryIndexError> {
    graphs::run(database_path, query)
}
