//! Bounded parse, publication, compaction, and graph resolution.

use std::mem;
use std::path::Path;

use rusqlite::Connection;

use crate::corpus::main::load_discovered_memory_corpus::load_discovered_memory_corpus;
use crate::corpus::models::MemoryCorpus;
use crate::engine::constants;
use crate::engine::errors::MemoryIndexError;
use crate::engine::helpers::publication::database::PublicationResult;
use crate::engine::helpers::publication::{documents, lists, references, sections, skills};
use crate::engine::helpers::reporting::diagnostics;
use crate::engine::models::IndexSummary;
use crate::graph::main::resolve_memory_graph::resolve_memory_graph;
use crate::source::models::DiscoveryResult;

pub(crate) fn build(
    mut discovery: DiscoveryResult,
    temporary_path: &Path,
    require_valid: bool,
) -> Result<PublicationResult, MemoryIndexError> {
    prepare_discovery(&mut discovery);
    let mut connection = open_database(temporary_path)?;
    let transaction = connection
        .transaction()
        .map_err(|error| MemoryIndexError::sqlite("begin memory index transaction", error))?;
    transaction
        .execute_batch(constants::MEMORY_SCHEMA_SQL)
        .map_err(|error| MemoryIndexError::sqlite("create memory schema", error))?;
    let source_diagnostics = mem::take(&mut discovery.diagnostics);
    let skill_files = mem::take(&mut discovery.skill_files);
    let discovered_documents = mem::take(&mut discovery.documents);
    let mut corpus = MemoryCorpus {
        documents: Vec::with_capacity(discovered_documents.len()),
        skill_files,
        source_diagnostics,
        diagnostics: Vec::new(),
    };
    let mut counts = PublicationCounts::default();
    for sources in discovered_documents.chunks(constants::PUBLICATION_DOCUMENT_CHUNK) {
        let chunk_discovery = DiscoveryResult {
            documents: sources.to_vec(),
            skill_files: Vec::new(),
            diagnostics: Vec::new(),
        };
        let mut chunk = load_discovered_memory_corpus(chunk_discovery);
        counts.publish_chunk(&transaction, &corpus, &chunk, corpus.documents.len())?;
        compact(&mut chunk);
        corpus.documents.append(&mut chunk.documents);
        corpus.diagnostics.append(&mut chunk.diagnostics);
    }
    corpus.diagnostics.sort_by(|left, right| {
        (&left.repository_relative_path, left.kind)
            .cmp(&(&right.repository_relative_path, right.kind))
    });
    counts.skill_file_count = skills::insert(&transaction, &corpus)?;
    let graph = resolve_memory_graph(&corpus);
    counts.link_count = references::insert_links(&transaction, &corpus, &graph)?;
    let findings = diagnostics::collect(&corpus, &graph);
    let summary = counts.summary(&corpus, graph.diagnostics.len());
    let published = !require_valid || findings.is_empty();
    if published {
        transaction
            .commit()
            .map_err(|error| MemoryIndexError::sqlite("commit memory index transaction", error))?;
    } else {
        transaction
            .rollback()
            .map_err(|error| MemoryIndexError::sqlite("rollback invalid memory index", error))?;
    }
    connection
        .close()
        .map_err(|(_, error)| MemoryIndexError::sqlite("close temporary memory index", error))?;
    Ok(PublicationResult {
        summary,
        diagnostics: findings,
        published,
    })
}

#[derive(Default)]
struct PublicationCounts {
    document_count: usize,
    section_count: usize,
    list_item_count: usize,
    list_item_batch_count: usize,
    max_loaded_document_batch: usize,
    link_count: usize,
    tag_count: usize,
    skill_file_count: usize,
}

impl PublicationCounts {
    fn publish_chunk(
        &mut self,
        transaction: &rusqlite::Transaction<'_>,
        retained: &MemoryCorpus,
        chunk: &MemoryCorpus,
        document_offset: usize,
    ) -> Result<(), MemoryIndexError> {
        let loaded_documents = retained_publication_documents(retained) + chunk.documents.len();
        self.max_loaded_document_batch = self.max_loaded_document_batch.max(loaded_documents);
        self.document_count += documents::insert(transaction, chunk, document_offset)?;
        self.section_count += sections::insert(transaction, chunk)?;
        let (items, batches) = lists::insert(transaction, chunk, document_offset)?;
        self.list_item_count += items;
        self.list_item_batch_count += batches;
        self.tag_count += references::insert_tags(transaction, chunk)?;
        Ok(())
    }

    fn summary(self, corpus: &MemoryCorpus, graph_diagnostic_count: usize) -> IndexSummary {
        IndexSummary {
            document_count: self.document_count,
            section_count: self.section_count,
            list_item_count: self.list_item_count,
            list_item_batch_count: self.list_item_batch_count,
            max_loaded_document_batch: self.max_loaded_document_batch,
            link_count: self.link_count,
            tag_count: self.tag_count,
            skill_file_count: self.skill_file_count,
            source_diagnostic_count: corpus.source_diagnostics.len(),
            corpus_diagnostic_count: corpus.diagnostics.len(),
            graph_diagnostic_count,
        }
    }
}

fn retained_publication_documents(corpus: &MemoryCorpus) -> usize {
    corpus
        .documents
        .iter()
        .filter(|document| {
            document.parsed_markdown.as_ref().is_some_and(|parsed| {
                !parsed.plain_text.is_empty()
                    || !parsed.preamble_raw_markdown.is_empty()
                    || !parsed.preamble_plain_text.is_empty()
                    || parsed
                        .headings
                        .iter()
                        .any(|heading| !heading.raw_source.is_empty())
                    || parsed.sections.iter().any(|section| {
                        !section.raw_markdown.is_empty() || !section.plain_text.is_empty()
                    })
                    || !parsed.list_items.is_empty()
                    || !parsed.code_blocks.is_empty()
                    || !parsed.tags.is_empty()
            })
        })
        .count()
}

fn open_database(path: &Path) -> Result<Connection, MemoryIndexError> {
    let connection = Connection::open(path)
        .map_err(|error| MemoryIndexError::sqlite("open temporary memory index", error))?;
    connection
        .execute_batch(
            "PRAGMA foreign_keys = ON; PRAGMA journal_mode = OFF; PRAGMA synchronous = OFF; PRAGMA temp_store = MEMORY;",
        )
        .map_err(|error| MemoryIndexError::sqlite("configure temporary memory index", error))?;
    Ok(connection)
}

fn prepare_discovery(discovery: &mut DiscoveryResult) {
    discovery.documents.sort_by(|left, right| {
        left.canonical_path
            .repository_relative
            .cmp(&right.canonical_path.repository_relative)
    });
    discovery.skill_files.sort_by(|left, right| {
        left.canonical_path
            .repository_relative
            .cmp(&right.canonical_path.repository_relative)
    });
    discovery.diagnostics.sort_by(|left, right| {
        (&left.repository_relative_path, left.kind)
            .cmp(&(&right.repository_relative_path, right.kind))
    });
}

fn compact(corpus: &mut MemoryCorpus) {
    for document in &mut corpus.documents {
        let Some(parsed) = &mut document.parsed_markdown else {
            continue;
        };
        parsed.plain_text.clear();
        parsed.preamble_raw_markdown.clear();
        parsed.preamble_plain_text.clear();
        for heading in &mut parsed.headings {
            heading.heading_path.clear();
            heading.raw_source.clear();
            heading.phase_identifier = None;
            heading.phase_title = None;
        }
        for section in &mut parsed.sections {
            section.heading_path.clear();
            section.raw_markdown.clear();
            section.plain_text.clear();
        }
        parsed.list_items.clear();
        parsed.list_items.shrink_to_fit();
        parsed.code_blocks.clear();
        parsed.code_blocks.shrink_to_fit();
        parsed.tags.clear();
        parsed.tags.shrink_to_fit();
    }
}
