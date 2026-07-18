//! Document source metadata and parsed-content publication.

use duckdb::{params, Transaction};

use crate::corpus::models::MemoryCorpus;
use crate::engine::errors::MemoryIndexError;
use crate::engine::helpers::publication::values;

pub(crate) fn insert(
    transaction: &Transaction<'_>,
    corpus: &MemoryCorpus,
) -> Result<usize, MemoryIndexError> {
    let mut appender = transaction
        .appender("documents")
        .map_err(|error| MemoryIndexError::duckdb("create document appender", error))?;
    for document in &corpus.documents {
        let source = &document.source;
        let parsed = document.parsed_markdown.as_ref();
        let diagnostic_count =
            values::document_diagnostic_count(corpus, &source.canonical_path.repository_relative);
        appender
            .append_row(params![
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
                source.metadata.byte_size,
                values::unix_nanoseconds(source.metadata.modified_at),
                source.metadata.changed_at.map(values::unix_nanoseconds),
                values::git_tracking(source.git_tracking),
                if parsed.is_some() { "valid" } else { "invalid" },
                diagnostic_count as u64,
                parsed.map(|value| value.raw_markdown.as_str()),
                parsed.map(|value| value.plain_text.as_str()),
                parsed.and_then(|value| value.title.as_deref()),
            ])
            .map_err(|error| MemoryIndexError::duckdb("append document", error))?;
    }
    appender
        .flush()
        .map_err(|error| MemoryIndexError::duckdb("flush document appender", error))?;
    Ok(corpus.documents.len())
}
