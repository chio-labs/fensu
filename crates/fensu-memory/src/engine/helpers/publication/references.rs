//! Markdown link, relationship, and tag publication.

use rusqlite::{params, Transaction};

use crate::corpus::models::MemoryCorpus;
use crate::engine::errors::MemoryIndexError;
use crate::engine::helpers::publication::values;
use crate::graph::models::MemoryGraph;

pub(crate) fn insert_links(
    transaction: &Transaction<'_>,
    corpus: &MemoryCorpus,
    graph: &MemoryGraph,
) -> Result<usize, MemoryIndexError> {
    let mut statement = transaction
        .prepare_cached(
            "INSERT INTO links VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?15, ?16, ?17, ?18, ?19, ?20)",
        )
        .map_err(|error| MemoryIndexError::sqlite("prepare link insertion", error))?;
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
            statement
                .execute(params![
                    &document.source.identity.0,
                    link.ordinal as i64,
                    values::section_ordinal(parsed, link.source_range.start_byte)
                        .map(|value| value as i64),
                    link.list_item_ordinal.map(|value| value as i64),
                    values::link_syntax(link.syntax_kind),
                    &link.target,
                    link.alias.as_deref(),
                    link.display.as_deref(),
                    link.heading_fragment.as_deref(),
                    resolved
                        .target_document_identity
                        .as_ref()
                        .map(|identity| identity.0.as_str()),
                    resolved.target_section_ordinal.map(|value| value as i64),
                    values::resolution_status(resolved.status),
                    link.relationship_kind.map(values::relationship_kind),
                    true,
                    &link.raw_source,
                    link.source_line as i64,
                    link.source_range.start_byte as i64,
                    link.source_range.end_byte as i64,
                    link.source_range.start_line as i64,
                    link.source_range.end_line as i64,
                ])
                .map_err(|error| MemoryIndexError::sqlite("insert link", error))?;
            count += 1;
        }
    }
    Ok(count)
}

pub(crate) fn insert_tags(
    transaction: &Transaction<'_>,
    corpus: &MemoryCorpus,
) -> Result<usize, MemoryIndexError> {
    let mut statement = transaction
        .prepare_cached("INSERT INTO tags VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10)")
        .map_err(|error| MemoryIndexError::sqlite("prepare tag insertion", error))?;
    let mut count = 0;
    for document in &corpus.documents {
        let Some(parsed) = &document.parsed_markdown else {
            continue;
        };
        for tag in &parsed.tags {
            statement
                .execute(params![
                    &document.source.identity.0,
                    tag.ordinal as i64,
                    values::section_ordinal(parsed, tag.source_range.start_byte)
                        .map(|value| value as i64),
                    &tag.name,
                    &tag.raw_source,
                    tag.source_line as i64,
                    tag.source_range.start_byte as i64,
                    tag.source_range.end_byte as i64,
                    tag.source_range.start_line as i64,
                    tag.source_range.end_line as i64,
                ])
                .map_err(|error| MemoryIndexError::sqlite("insert tag", error))?;
            count += 1;
        }
    }
    Ok(count)
}
