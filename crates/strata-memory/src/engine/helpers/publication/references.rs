//! Markdown link, relationship, and tag publication.

use duckdb::{params, Transaction};

use crate::corpus::models::MemoryCorpus;
use crate::engine::errors::MemoryIndexError;
use crate::engine::helpers::publication::values;
use crate::graph::models::MemoryGraph;

pub(crate) fn insert_links(
    transaction: &Transaction<'_>,
    corpus: &MemoryCorpus,
    graph: &MemoryGraph,
) -> Result<usize, MemoryIndexError> {
    let mut appender = transaction
        .appender("links")
        .map_err(|error| MemoryIndexError::duckdb("create link appender", error))?;
    let mut count = 0;
    for document in &corpus.documents {
        let Some(parsed) = &document.parsed_markdown else {
            continue;
        };
        for link in &parsed.links {
            let resolved = graph
                .links
                .iter()
                .find(|candidate| {
                    candidate.source_document_identity == document.source.identity
                        && candidate.source_link_ordinal == link.ordinal
                })
                .ok_or_else(|| MemoryIndexError::MissingResolvedLink {
                    document_identity: document.source.identity.0.clone(),
                    link_ordinal: link.ordinal,
                })?;
            appender
                .append_row(params![
                    &document.source.identity.0,
                    link.ordinal as u64,
                    values::section_ordinal(parsed, link.source_range.start_byte)
                        .map(|value| value as u64),
                    link.list_item_ordinal.map(|value| value as u64),
                    values::link_syntax(link.syntax_kind),
                    &link.target,
                    link.alias.as_deref(),
                    link.display.as_deref(),
                    link.heading_fragment.as_deref(),
                    resolved
                        .target_document_identity
                        .as_ref()
                        .map(|identity| identity.0.as_str()),
                    resolved.target_section_ordinal.map(|value| value as u64),
                    values::resolution_status(resolved.status),
                    link.relationship_kind.map(values::relationship_kind),
                    true,
                    &link.raw_source,
                    link.source_line as u64,
                    link.source_range.start_byte as u64,
                    link.source_range.end_byte as u64,
                    link.source_range.start_line as u64,
                    link.source_range.end_line as u64,
                ])
                .map_err(|error| MemoryIndexError::duckdb("append link", error))?;
            count += 1;
        }
    }
    appender
        .flush()
        .map_err(|error| MemoryIndexError::duckdb("flush link appender", error))?;
    Ok(count)
}

pub(crate) fn insert_tags(
    transaction: &Transaction<'_>,
    corpus: &MemoryCorpus,
) -> Result<usize, MemoryIndexError> {
    let mut appender = transaction
        .appender("tags")
        .map_err(|error| MemoryIndexError::duckdb("create tag appender", error))?;
    let mut count = 0;
    for document in &corpus.documents {
        let Some(parsed) = &document.parsed_markdown else {
            continue;
        };
        for tag in &parsed.tags {
            appender
                .append_row(params![
                    &document.source.identity.0,
                    tag.ordinal as u64,
                    values::section_ordinal(parsed, tag.source_range.start_byte)
                        .map(|value| value as u64),
                    &tag.name,
                    &tag.raw_source,
                    tag.source_line as u64,
                    tag.source_range.start_byte as u64,
                    tag.source_range.end_byte as u64,
                    tag.source_range.start_line as u64,
                    tag.source_range.end_line as u64,
                ])
                .map_err(|error| MemoryIndexError::duckdb("append tag", error))?;
            count += 1;
        }
    }
    appender
        .flush()
        .map_err(|error| MemoryIndexError::duckdb("flush tag appender", error))?;
    Ok(count)
}
