//! Nested skill support-file publication.

use duckdb::{params, Transaction};

use crate::corpus::models::MemoryCorpus;
use crate::engine::errors::MemoryIndexError;
use crate::engine::helpers::publication::values;
use crate::source::types::ArchiveState;

pub(crate) fn insert(
    transaction: &Transaction<'_>,
    corpus: &MemoryCorpus,
) -> Result<usize, MemoryIndexError> {
    let mut appender = transaction
        .appender("skill_files")
        .map_err(|error| MemoryIndexError::duckdb("create skill file appender", error))?;
    for file in &corpus.skill_files {
        let archived = matches!(file.canonical_path.archive_state, ArchiveState::Archived);
        appender
            .append_row(params![
                &file.skill_identity.0,
                &file.canonical_path.repository_relative,
                values::filesystem_path(&file.canonical_path.filesystem_path),
                &file.bundle_relative_path,
                &file.metadata.content_sha256,
                file.metadata.byte_size,
                values::unix_nanoseconds(file.metadata.modified_at),
                file.metadata.changed_at.map(values::unix_nanoseconds),
                values::git_tracking(file.git_tracking),
                archived,
                !archived,
            ])
            .map_err(|error| MemoryIndexError::duckdb("append skill file", error))?;
    }
    appender
        .flush()
        .map_err(|error| MemoryIndexError::duckdb("flush skill file appender", error))?;
    Ok(corpus.skill_files.len())
}
