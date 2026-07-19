//! Resolve corpus links and derive task dependency graph data.

use crate::corpus::models::MemoryCorpus;
use crate::graph::helpers::{dependencies, link_resolution};
use crate::graph::models::MemoryGraph;

/// Return deterministic resolved links, dependency edges, and graph diagnostics.
pub fn resolve_memory_graph(corpus: &MemoryCorpus) -> MemoryGraph {
    let resolution = link_resolution::resolve(corpus);
    let dependency_graph = dependencies::analyze(corpus, &resolution.links);
    let mut diagnostics = resolution.diagnostics;
    diagnostics.extend(dependency_graph.diagnostics);
    diagnostics.sort();
    MemoryGraph {
        links: resolution.links,
        dependencies: dependency_graph.edges,
        diagnostics,
    }
}
