//! Markdown list item and checkbox publication.

use rusqlite::types::Value;
use rusqlite::{params_from_iter, Transaction};

use crate::corpus::models::MemoryCorpus;
use crate::engine::helpers::publication::values;
use crate::engine::{constants, errors::MemoryIndexError};
use crate::markdown::models::MarkdownListItem;
use crate::markdown::types::ListKind;

const LIST_ITEM_COLUMN_COUNT: usize = 18;
const SQLITE_INSERT_ROWS: usize = 1_000;

struct ListItemRow<'item> {
    document_key: i64,
    item: &'item MarkdownListItem,
}

pub(crate) fn insert(
    transaction: &Transaction<'_>,
    corpus: &MemoryCorpus,
) -> Result<(usize, usize), MemoryIndexError> {
    let mut rows = Vec::with_capacity(constants::MEMORY_PUBLICATION_BATCH_ROWS);
    let mut count = 0;
    let mut batch_count = 0;
    for (document_index, document) in corpus.documents.iter().enumerate() {
        let Some(parsed) = &document.parsed_markdown else {
            continue;
        };
        for item in &parsed.list_items {
            rows.push(ListItemRow {
                document_key: document_index as i64,
                item,
            });
            if rows.len() == constants::MEMORY_PUBLICATION_BATCH_ROWS {
                batch_count += append_batch(transaction, &rows)?;
                rows.clear();
            }
            count += 1;
        }
    }
    if !rows.is_empty() {
        batch_count += append_batch(transaction, &rows)?;
    }
    Ok((count, batch_count))
}

fn append_batch(
    transaction: &Transaction<'_>,
    rows: &[ListItemRow<'_>],
) -> Result<usize, MemoryIndexError> {
    let mut batch_count = 0;
    for chunk in rows.chunks(SQLITE_INSERT_ROWS) {
        let sql = insert_sql(chunk.len());
        let mut parameters = Vec::with_capacity(chunk.len() * LIST_ITEM_COLUMN_COUNT);
        for row in chunk {
            append_parameters(&mut parameters, row);
        }
        transaction
            .prepare_cached(&sql)
            .and_then(|mut statement| statement.execute(params_from_iter(parameters.iter())))
            .map_err(|error| MemoryIndexError::sqlite("insert list item batch", error))?;
        batch_count += 1;
    }
    Ok(batch_count)
}

fn append_parameters(parameters: &mut Vec<Value>, row: &ListItemRow<'_>) {
    let item = row.item;
    let kind = match item.kind {
        ListKind::Unordered => constants::LIST_KIND_UNORDERED_CODE,
        ListKind::Ordered => constants::LIST_KIND_ORDERED_CODE,
    };
    parameters.extend([
        Value::Integer(row.document_key),
        Value::Integer(item.ordinal as i64),
        optional_integer(item.section_ordinal),
        optional_integer(item.parent_ordinal),
        Value::Integer(i64::from(kind)),
        Value::Integer(item.nesting_depth as i64),
        item.ordered_number
            .map_or(Value::Null, |value| Value::Integer(value as i64)),
        Value::Integer((item.source_range.start_byte + item.raw_markdown.len()) as i64),
        Value::Text(item.plain_text.clone()),
        Value::Integer(item.source_line as i64),
        Value::Integer(item.source_range.start_byte as i64),
        Value::Integer(item.source_range.end_byte as i64),
        Value::Integer(item.source_range.start_line as i64),
        Value::Integer(item.source_range.end_line as i64),
        item.checkbox
            .as_ref()
            .map_or(Value::Null, |value| Value::Text(value.raw_marker.clone())),
        item.checkbox.as_ref().map_or(Value::Null, |value| {
            Value::Text(values::checkbox_state(value.state).to_owned())
        }),
        item.leading_key
            .as_ref()
            .map_or(Value::Null, |value| Value::Text(value.clone())),
        item.relationship_kind.map_or(Value::Null, |value| {
            Value::Text(values::relationship_kind(value).to_owned())
        }),
    ]);
}

fn optional_integer(value: Option<usize>) -> Value {
    value.map_or(Value::Null, |number| Value::Integer(number as i64))
}

fn insert_sql(row_count: usize) -> String {
    let row = format!("({})", vec!["?"; LIST_ITEM_COLUMN_COUNT].join(", "));
    format!(
        "INSERT INTO _list_items VALUES {}",
        vec![row; row_count].join(", ")
    )
}
