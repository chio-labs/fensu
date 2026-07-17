//! Rebuild and atomically publish one repository memory index.

use std::path::Path;

use crate::corpus::main::load_memory_corpus::load_memory_corpus;
use crate::engine::errors::MemoryIndexError;
use crate::engine::helpers::publication::database;
use crate::engine::models::IndexSummary;
use crate::graph::main::resolve_memory_graph::resolve_memory_graph;

/// Load the complete corpus and atomically replace its DuckDB index.
pub fn rebuild_memory_index(
    repository_root: &Path,
    database_path: &Path,
) -> Result<IndexSummary, MemoryIndexError> {
    let corpus = load_memory_corpus(repository_root);
    let graph = resolve_memory_graph(&corpus);
    database::publish(&corpus, &graph, database_path)
}
