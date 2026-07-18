//! Synthetic preamble and authored section publication.

use duckdb::{params, Transaction};

use crate::corpus::models::MemoryCorpus;
use crate::engine::errors::MemoryIndexError;
use crate::engine::helpers::publication::values;

pub(crate) fn insert(
    transaction: &Transaction<'_>,
    corpus: &MemoryCorpus,
) -> Result<usize, MemoryIndexError> {
    let mut appender = transaction
        .appender("sections")
        .map_err(|error| MemoryIndexError::duckdb("create section appender", error))?;
    let mut count = 0;
    for document in &corpus.documents {
        let Some(parsed) = &document.parsed_markdown else {
            continue;
        };
        if let Some(range) = values::preamble_range(parsed) {
            appender
                .append_row(params![
                    &document.source.identity.0,
                    0_u64,
                    None::<u64>,
                    None::<u8>,
                    None::<&str>,
                    None::<&str>,
                    None::<&str>,
                    None::<&str>,
                    None::<&str>,
                    None::<&str>,
                    &parsed.preamble_raw_markdown,
                    &parsed.preamble_plain_text,
                    range.start_byte as u64,
                    range.end_byte as u64,
                    range.start_line as u64,
                    range.end_line as u64,
                ])
                .map_err(|error| MemoryIndexError::duckdb("append preamble section", error))?;
            count += 1;
        }
        for section in &parsed.sections {
            let heading = parsed
                .headings
                .iter()
                .find(|heading| heading.ordinal == section.heading_ordinal);
            let heading_path = values::heading_path(&section.heading_path);
            appender
                .append_row(params![
                    &document.source.identity.0,
                    section.ordinal as u64,
                    Some(section.heading_ordinal as u64),
                    heading.map(|value| value.level),
                    heading.map(|value| value.text.as_str()),
                    heading.map(|value| value.slug.as_str()),
                    heading_path,
                    heading
                        .and_then(|value| value.semantic_kind)
                        .map(values::semantic_kind),
                    heading.and_then(|value| value.phase_identifier.as_deref()),
                    heading.and_then(|value| value.phase_title.as_deref()),
                    &section.raw_markdown,
                    &section.plain_text,
                    section.source_range.start_byte as u64,
                    section.source_range.end_byte as u64,
                    section.source_range.start_line as u64,
                    section.source_range.end_line as u64,
                ])
                .map_err(|error| MemoryIndexError::duckdb("append authored section", error))?;
            count += 1;
        }
    }
    appender
        .flush()
        .map_err(|error| MemoryIndexError::duckdb("flush section appender", error))?;
    Ok(count)
}
