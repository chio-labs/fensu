//! Document source metadata and parsed-content publication.

use rusqlite::{params, Transaction};

use crate::corpus::models::MemoryCorpus;
use crate::engine::errors::MemoryIndexError;
use crate::engine::helpers::publication::values;

pub(crate) fn insert(
    transaction: &Transaction<'_>,
    corpus: &MemoryCorpus,
    document_offset: usize,
) -> Result<usize, MemoryIndexError> {
    let mut statement = transaction
        .prepare_cached(
            "INSERT INTO documents VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?15, ?16, ?17, ?18, ?19, ?20)",
        )
        .map_err(|error| MemoryIndexError::sqlite("prepare document insertion", error))?;
    for document in &corpus.documents {
        let source = &document.source;
        let parsed = document.parsed_markdown.as_ref();
        let diagnostic_count =
            values::document_diagnostic_count(corpus, &source.canonical_path.repository_relative);
        statement
            .execute(params![
                &source.identity.0,
                values::artifact_kind(source.artifact_kind),
                source.task_category.map(values::task_category),
                source.lifecycle.map(values::lifecycle),
                values::archive_state(source.canonical_path.archive_state),
                &source.canonical_path.repository_relative,
                values::filesystem_path(&source.canonical_path.filesystem_path),
                &source.basename,
                &source.slug,
                source.creation_timestamp.as_deref(),
                &source.metadata.content_sha256,
                source.metadata.byte_size as i64,
                values::unix_nanoseconds(source.metadata.modified_at),
                source.metadata.changed_at.map(values::unix_nanoseconds),
                values::git_tracking(source.git_tracking),
                if parsed.is_some() { "valid" } else { "invalid" },
                diagnostic_count as i64,
                parsed.map(|value| value.raw_markdown.as_str()),
                parsed.map(|value| value.plain_text.as_str()),
                parsed.and_then(|value| value.title.as_deref()),
            ])
            .map_err(|error| MemoryIndexError::sqlite("insert document", error))?;
    }
    drop(statement);
    let mut key_statement = transaction
        .prepare_cached("INSERT INTO _document_keys VALUES (?1, ?2)")
        .map_err(|error| MemoryIndexError::sqlite("prepare document key insertion", error))?;
    for (index, document) in corpus.documents.iter().enumerate() {
        key_statement
            .execute(params![
                (document_offset + index) as i64,
                &document.source.identity.0
            ])
            .map_err(|error| MemoryIndexError::sqlite("insert document key", error))?;
    }
    Ok(corpus.documents.len())
}
