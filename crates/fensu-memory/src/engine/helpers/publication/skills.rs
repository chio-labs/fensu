//! Nested skill support-file publication.

use rusqlite::{params, Transaction};

use crate::corpus::models::MemoryCorpus;
use crate::engine::errors::MemoryIndexError;
use crate::engine::helpers::publication::values;
use crate::source::types::ArchiveState;

pub(crate) fn insert(
    transaction: &Transaction<'_>,
    corpus: &MemoryCorpus,
) -> Result<usize, MemoryIndexError> {
    let mut statement = transaction
        .prepare_cached(
            "INSERT INTO skill_files VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11)",
        )
        .map_err(|error| MemoryIndexError::sqlite("prepare skill file insertion", error))?;
    for file in &corpus.skill_files {
        let archived = matches!(file.canonical_path.archive_state, ArchiveState::Archived);
        statement
            .execute(params![
                &file.skill_identity.0,
                &file.canonical_path.repository_relative,
                values::filesystem_path(&file.canonical_path.filesystem_path),
                &file.bundle_relative_path,
                &file.metadata.content_sha256,
                file.metadata.byte_size as i64,
                values::unix_nanoseconds(file.metadata.modified_at),
                file.metadata.changed_at.map(values::unix_nanoseconds),
                values::git_tracking(file.git_tracking),
                archived,
                !archived,
            ])
            .map_err(|error| MemoryIndexError::sqlite("insert skill file", error))?;
    }
    Ok(corpus.skill_files.len())
}
