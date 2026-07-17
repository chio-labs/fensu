//! Markdown list item and checkbox publication.

use duckdb::{params, Transaction};

use crate::corpus::models::MemoryCorpus;
use crate::engine::constants;
use crate::engine::errors::MemoryIndexError;
use crate::engine::helpers::publication::values;

pub(crate) fn insert(
    transaction: &Transaction<'_>,
    corpus: &MemoryCorpus,
) -> Result<usize, MemoryIndexError> {
    let mut statement = transaction
        .prepare(constants::LIST_ITEM_INSERT_SQL)
        .map_err(|error| MemoryIndexError::duckdb("prepare list item insertion", error))?;
    let mut count = 0;
    for document in &corpus.documents {
        let Some(parsed) = &document.parsed_markdown else {
            continue;
        };
        for item in &parsed.list_items {
            let heading_path = values::heading_path(&item.heading_path);
            statement
                .execute(params![
                    &document.source.identity.0,
                    item.ordinal as u64,
                    values::section_ordinal(parsed, item.source_range.start_byte)
                        .map(|value| value as u64),
                    item.parent_ordinal.map(|value| value as u64),
                    values::list_kind(item.kind),
                    item.nesting_depth as u64,
                    item.ordered_number,
                    heading_path,
                    &item.raw_markdown,
                    &item.plain_text,
                    item.source_line as u64,
                    item.source_range.start_byte as u64,
                    item.source_range.end_byte as u64,
                    item.source_range.start_line as u64,
                    item.source_range.end_line as u64,
                    item.checkbox
                        .as_ref()
                        .map(|value| value.raw_marker.as_str()),
                    item.checkbox
                        .as_ref()
                        .map(|value| values::checkbox_state(value.state)),
                    item.leading_key.as_deref(),
                    item.relationship_kind.map(values::relationship_kind),
                ])
                .map_err(|error| MemoryIndexError::duckdb("insert list item", error))?;
            count += 1;
        }
    }
    Ok(count)
}
