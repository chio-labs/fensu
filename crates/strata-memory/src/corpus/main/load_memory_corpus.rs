//! Discover, load, and validate one repository memory corpus.

use std::path::Path;

use crate::corpus::main::load_discovered_memory_corpus::load_discovered_memory_corpus;
use crate::corpus::models::MemoryCorpus;
use crate::source::main::discover_memory::discover_memory;

/// Return all discovered sources, parsed documents, and recoverable diagnostics.
pub fn load_memory_corpus(repository_root: &Path) -> MemoryCorpus {
    let discovery = discover_memory(repository_root);
    load_discovered_memory_corpus(discovery)
}
