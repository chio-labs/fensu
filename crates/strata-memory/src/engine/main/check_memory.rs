//! Validate canonical memory directly and publish only a valid loaded corpus.

use std::path::Path;

use crate::corpus::main::load_memory_corpus::load_memory_corpus;
use crate::engine::errors::MemoryIndexError;
use crate::engine::helpers::publication::database;
use crate::engine::helpers::reporting::diagnostics;
use crate::engine::models::MemoryCheckResult;
use crate::graph::main::resolve_memory_graph::resolve_memory_graph;

/// Return direct-source findings and publish the already-loaded valid corpus.
pub fn check_memory(
    repository_root: &Path,
    database_path: &Path,
) -> Result<MemoryCheckResult, MemoryIndexError> {
    let corpus = load_memory_corpus(repository_root);
    let graph = resolve_memory_graph(&corpus);
    let findings = diagnostics::collect(&corpus, &graph);
    let published = if findings.is_empty() {
        Some(database::publish(&corpus, &graph, database_path)?)
    } else {
        None
    };
    Ok(MemoryCheckResult {
        diagnostics: findings,
        published,
    })
}
