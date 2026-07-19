//! Summarize live repository memory without reading or writing an index.

use std::path::Path;

use crate::corpus::main::load_memory_corpus::load_memory_corpus;
use crate::engine::helpers::reporting::summaries;
use crate::engine::models::MemorySummary;
use crate::graph::main::resolve_memory_graph::resolve_memory_graph;

/// Return the nine publication counts from the live corpus and resolved graph.
pub fn summarize_memory(repository_root: &Path) -> MemorySummary {
    let corpus = load_memory_corpus(repository_root);
    let graph = resolve_memory_graph(&corpus);
    summaries::summarize(&corpus, &graph)
}
