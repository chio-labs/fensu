//! Live corpus and graph count derivation.

use crate::corpus::models::MemoryCorpus;
use crate::engine::models::MemorySummary;
use crate::graph::models::MemoryGraph;

pub(crate) fn summarize(corpus: &MemoryCorpus, graph: &MemoryGraph) -> MemorySummary {
    let mut section_count = 0;
    let mut list_item_count = 0;
    let mut tag_count = 0;
    for document in &corpus.documents {
        let Some(parsed) = &document.parsed_markdown else {
            continue;
        };
        section_count += parsed.sections.len();
        section_count += usize::from(!parsed.preamble_plain_text.trim().is_empty());
        list_item_count += parsed.list_items.len();
        tag_count += parsed.tags.len();
    }
    MemorySummary {
        document_count: corpus.documents.len(),
        section_count,
        list_item_count,
        link_count: graph.links.len(),
        tag_count,
        skill_file_count: corpus.skill_files.len(),
        source_diagnostic_count: corpus.source_diagnostics.len(),
        corpus_diagnostic_count: corpus.diagnostics.len(),
        graph_diagnostic_count: graph.diagnostics.len(),
    }
}
