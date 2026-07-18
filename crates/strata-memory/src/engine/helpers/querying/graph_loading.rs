//! Read graph documents and links from the published memory index.

use std::collections::HashSet;

use rusqlite::Connection;

use crate::engine::errors::MemoryIndexError;
use crate::engine::models::MemoryGraphRelationship;

#[derive(Clone, Debug)]
pub(super) struct DocumentRow {
    pub(super) identity: String,
    pub(super) artifact_kind: String,
    pub(super) archive_state: String,
    pub(super) repository_relative_path: String,
    pub(super) basename: String,
    pub(super) slug: String,
    pub(super) title: Option<String>,
}

#[derive(Clone, Debug)]
pub(super) struct LinkRow {
    pub(super) source: String,
    pub(super) ordinal: usize,
    pub(super) target: String,
    pub(super) status: String,
    pub(super) target_identity: Option<String>,
    pub(super) relationship: String,
}

pub(super) fn load_documents(
    connection: &Connection,
) -> Result<Vec<DocumentRow>, MemoryIndexError> {
    let mut statement = connection
        .prepare(
            "SELECT identity, artifact_kind, archive_state, repository_relative_path, basename, slug, title FROM documents ORDER BY identity",
        )
        .map_err(|error| MemoryIndexError::sqlite("prepare memory graph documents", error))?;
    let rows = statement
        .query_map([], |row| {
            Ok(DocumentRow {
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
    rows.collect::<Result<Vec<DocumentRow>, _>>()
        .map_err(|error| MemoryIndexError::sqlite("decode memory graph document", error))
}

pub(super) fn load_links(
    connection: &Connection,
    relationships: &[MemoryGraphRelationship],
) -> Result<Vec<LinkRow>, MemoryIndexError> {
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
            Ok(LinkRow {
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
        .collect::<Result<Vec<LinkRow>, _>>()
        .map_err(|error| MemoryIndexError::sqlite("decode memory graph link", error))?;
    if selected.is_empty() {
        return Ok(decoded);
    }
    Ok(decoded
        .into_iter()
        .filter(|link| selected.contains(link.relationship.as_str()))
        .collect())
}
