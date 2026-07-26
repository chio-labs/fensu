//! Read graph documents and links from the published memory index.

use std::collections::HashSet;

use rusqlite::Connection;

use crate::engine::errors::MemoryIndexError;
use crate::engine::models::{GraphDocumentRow, GraphLinkRow, MemoryGraphRelationship};

pub(super) fn load_documents(
    connection: &Connection,
) -> Result<Vec<GraphDocumentRow>, MemoryIndexError> {
    let mut statement = connection
        .prepare(
            "SELECT identity, artifact_kind, archive_state, repository_relative_path, basename, slug, title FROM documents ORDER BY identity",
        )
        .map_err(|error| MemoryIndexError::sqlite("prepare memory graph documents", error))?;
    let rows = statement
        .query_map([], |row| {
            Ok(GraphDocumentRow {
                identity: row.get(0)?,
                artifact_kind: row.get(1)?,
                archive_state: row.get(2)?,
                repository_relative_path: row.get(3)?,
                basename: row.get(4)?,
                slug: row.get(5)?,
                title: row.get(6)?,
            })
        })
        .map_err(|error| MemoryIndexError::sqlite("query memory graph documents", error))?;
    rows.collect::<Result<Vec<GraphDocumentRow>, _>>()
        .map_err(|error| MemoryIndexError::sqlite("decode memory graph document", error))
}

pub(super) fn load_links(
    connection: &Connection,
    relationships: &[MemoryGraphRelationship],
) -> Result<Vec<GraphLinkRow>, MemoryIndexError> {
    let selected = relationships
        .iter()
        .map(|value| value.as_str())
        .collect::<HashSet<&str>>();
    let mut statement = connection
        .prepare(
            "SELECT document_identity, ordinal, target, resolution_status, resolved_document_identity, coalesce(relationship_kind, 'link') FROM links ORDER BY document_identity, ordinal",
        )
        .map_err(|error| MemoryIndexError::sqlite("prepare memory graph links", error))?;
    let rows = statement
        .query_map([], |row| {
            Ok(GraphLinkRow {
                source: row.get(0)?,
                ordinal: row.get::<_, i64>(1)? as usize,
                target: row.get(2)?,
                status: row.get(3)?,
                target_identity: row.get(4)?,
                relationship: row.get(5)?,
            })
        })
        .map_err(|error| MemoryIndexError::sqlite("query memory graph links", error))?;
    let decoded = rows
        .collect::<Result<Vec<GraphLinkRow>, _>>()
        .map_err(|error| MemoryIndexError::sqlite("decode memory graph link", error))?;
    if selected.is_empty() {
        return Ok(decoded);
    }
    Ok(decoded
        .into_iter()
        .filter(|link| selected.contains(link.relationship.as_str()))
        .collect())
}
