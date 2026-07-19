//! Load and validate an already discovered canonical corpus.

use crate::corpus::helpers::loading;
use crate::corpus::models::MemoryCorpus;
use crate::source::models::DiscoveryResult;

pub(crate) fn load_discovered_memory_corpus(discovery: DiscoveryResult) -> MemoryCorpus {
    loading::load(discovery)
}
