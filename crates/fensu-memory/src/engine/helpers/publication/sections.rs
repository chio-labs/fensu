//! Synthetic preamble and authored section publication.

use rusqlite::{params, Transaction};

use crate::corpus::models::MemoryCorpus;
use crate::engine::errors::MemoryIndexError;
use crate::engine::helpers::publication::values;

pub(crate) fn insert(
    transaction: &Transaction<'_>,
    corpus: &MemoryCorpus,
) -> Result<usize, MemoryIndexError> {
    let mut statement = transaction
        .prepare_cached(
            "INSERT INTO sections VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?15, ?16)",
        )
        .map_err(|error| MemoryIndexError::sqlite("prepare section insertion", error))?;
    let mut count = 0;
    for document in &corpus.documents {
        let Some(parsed) = &document.parsed_markdown else {
            continue;
        };
        if let Some(range) = values::preamble_range(parsed) {
            let heading_path = parsed
                .headings
                .iter()
                .find(|heading| heading.level == 1)
                .map_or_else(String::new, |heading| {
                    values::heading_path(&heading.heading_path)
                });
            statement
                .execute(params![
                    &document.source.identity.0,
                    0_i64,
                    None::<i64>,
                    None::<i64>,
                    None::<&str>,
                    None::<&str>,
                    heading_path,
                    None::<&str>,
                    None::<&str>,
                    None::<&str>,
                    &parsed.preamble_raw_markdown,
                    &parsed.preamble_plain_text,
                    range.start_byte as i64,
                    range.end_byte as i64,
                    range.start_line as i64,
                    range.end_line as i64,
                ])
                .map_err(|error| MemoryIndexError::sqlite("insert preamble section", error))?;
            count += 1;
        }
        for section in &parsed.sections {
            let heading = parsed
                .headings
                .iter()
                .find(|heading| heading.ordinal == section.heading_ordinal);
            let heading_path = values::heading_path(&section.heading_path);
            statement
                .execute(params![
                    &document.source.identity.0,
                    section.ordinal as i64,
                    Some(section.heading_ordinal as i64),
                    heading.map(|value| i64::from(value.level)),
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
                    section.source_range.start_byte as i64,
                    section.source_range.end_byte as i64,
                    section.source_range.start_line as i64,
                    section.source_range.end_line as i64,
                ])
                .map_err(|error| MemoryIndexError::sqlite("insert authored section", error))?;
            count += 1;
        }
    }
    Ok(count)
}
