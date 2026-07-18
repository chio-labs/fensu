//! Markdown list item and checkbox publication.

use std::sync::Arc;

use duckdb::arrow::array::{ArrayRef, StringArray, UInt64Array, UInt8Array};
use duckdb::arrow::datatypes::{DataType, Field, Schema};
use duckdb::arrow::record_batch::RecordBatch;
use duckdb::{Appender, Transaction};

use crate::corpus::models::MemoryCorpus;
use crate::engine::helpers::publication::values;
use crate::engine::{constants, errors::MemoryIndexError};
use crate::markdown::models::MarkdownListItem;
use crate::markdown::types::ListKind;

struct ListItemRow<'item> {
    document_key: u64,
    item: &'item MarkdownListItem,
}

#[derive(Clone, Copy, Default)]
struct OptionalListColumns {
    checkbox: bool,
    leading_key: bool,
    relationship_kind: bool,
}

pub(crate) fn insert(
    transaction: &Transaction<'_>,
    corpus: &MemoryCorpus,
) -> Result<(usize, usize), MemoryIndexError> {
    let optional = optional_columns(corpus);
    let column_names = list_item_column_names(optional);
    let mut appender = transaction
        .appender_with_columns("_list_items", &column_names)
        .map_err(|error| MemoryIndexError::duckdb("create list item appender", error))?;
    let schema = list_item_schema(optional);
    let mut rows = Vec::with_capacity(constants::MEMORY_PUBLICATION_BATCH_ROWS);
    let mut count = 0;
    let mut batch_count = 0;
    for (document_index, document) in corpus.documents.iter().enumerate() {
        let Some(parsed) = &document.parsed_markdown else {
            continue;
        };
        for item in &parsed.list_items {
            rows.push(ListItemRow {
                document_key: document_index as u64,
                item,
            });
            if rows.len() == constants::MEMORY_PUBLICATION_BATCH_ROWS {
                append_batch(&mut appender, &schema, &rows, optional)?;
                batch_count += 1;
                rows.clear();
            }
            count += 1;
        }
    }
    if !rows.is_empty() {
        append_batch(&mut appender, &schema, &rows, optional)?;
        batch_count += 1;
    }
    appender
        .flush()
        .map_err(|error| MemoryIndexError::duckdb("flush list item appender", error))?;
    Ok((count, batch_count))
}

fn append_batch(
    appender: &mut Appender<'_>,
    schema: &Arc<Schema>,
    rows: &[ListItemRow<'_>],
    optional: OptionalListColumns,
) -> Result<(), MemoryIndexError> {
    if rows.is_empty() {
        return Ok(());
    }
    let batch = RecordBatch::try_new(Arc::clone(schema), list_item_columns(rows, optional))
        .map_err(|error| MemoryIndexError::arrow("build list item record batch", error))?;
    appender
        .append_record_batch(batch)
        .map_err(|error| MemoryIndexError::duckdb("append list item record batch", error))
}

fn list_item_columns(rows: &[ListItemRow<'_>], optional: OptionalListColumns) -> Vec<ArrayRef> {
    let mut columns: Vec<ArrayRef> = vec![
        Arc::new(UInt64Array::from_iter_values(
            rows.iter().map(|row| row.document_key),
        )),
        Arc::new(UInt64Array::from_iter_values(
            rows.iter().map(|row| row.item.ordinal as u64),
        )),
        Arc::new(UInt64Array::from_iter(
            rows.iter()
                .map(|row| row.item.section_ordinal.map(|value| value as u64)),
        )),
        Arc::new(UInt64Array::from_iter(
            rows.iter()
                .map(|row| row.item.parent_ordinal.map(|value| value as u64)),
        )),
        Arc::new(UInt8Array::from_iter_values(rows.iter().map(
            |row| match row.item.kind {
                ListKind::Unordered => constants::LIST_KIND_UNORDERED_CODE,
                ListKind::Ordered => constants::LIST_KIND_ORDERED_CODE,
            },
        ))),
        Arc::new(UInt64Array::from_iter_values(
            rows.iter().map(|row| row.item.nesting_depth as u64),
        )),
        Arc::new(UInt64Array::from_iter(
            rows.iter().map(|row| row.item.ordered_number),
        )),
        Arc::new(UInt64Array::from_iter_values(rows.iter().map(|row| {
            (row.item.source_range.start_byte + row.item.raw_markdown.len()) as u64
        }))),
        Arc::new(StringArray::from_iter_values(
            rows.iter().map(|row| row.item.plain_text.as_str()),
        )),
        Arc::new(UInt64Array::from_iter_values(
            rows.iter().map(|row| row.item.source_line as u64),
        )),
        Arc::new(UInt64Array::from_iter_values(
            rows.iter()
                .map(|row| row.item.source_range.start_byte as u64),
        )),
        Arc::new(UInt64Array::from_iter_values(
            rows.iter().map(|row| row.item.source_range.end_byte as u64),
        )),
        Arc::new(UInt64Array::from_iter_values(
            rows.iter()
                .map(|row| row.item.source_range.start_line as u64),
        )),
        Arc::new(UInt64Array::from_iter_values(
            rows.iter().map(|row| row.item.source_range.end_line as u64),
        )),
    ];
    if optional.checkbox {
        columns.push(Arc::new(StringArray::from_iter(rows.iter().map(|row| {
            row.item
                .checkbox
                .as_ref()
                .map(|value| value.raw_marker.as_str())
        }))));
        columns.push(Arc::new(StringArray::from_iter(rows.iter().map(|row| {
            row.item
                .checkbox
                .as_ref()
                .map(|value| values::checkbox_state(value.state))
        }))));
    }
    if optional.leading_key {
        columns.push(Arc::new(StringArray::from_iter(
            rows.iter().map(|row| row.item.leading_key.as_deref()),
        )));
    }
    if optional.relationship_kind {
        columns.push(Arc::new(StringArray::from_iter(rows.iter().map(|row| {
            row.item.relationship_kind.map(values::relationship_kind)
        }))));
    }
    columns
}

fn list_item_schema(optional: OptionalListColumns) -> Arc<Schema> {
    let mut fields = vec![
        Field::new("document_key", DataType::UInt64, false),
        Field::new("ordinal", DataType::UInt64, false),
        Field::new("section_ordinal", DataType::UInt64, true),
        Field::new("parent_ordinal", DataType::UInt64, true),
        Field::new("kind", DataType::UInt8, false),
        Field::new("nesting_depth", DataType::UInt64, false),
        Field::new("ordered_number", DataType::UInt64, true),
        Field::new("raw_end_byte", DataType::UInt64, false),
        Field::new("plain_text", DataType::Utf8, false),
        Field::new("source_line", DataType::UInt64, false),
        Field::new("start_byte", DataType::UInt64, false),
        Field::new("end_byte", DataType::UInt64, false),
        Field::new("start_line", DataType::UInt64, false),
        Field::new("end_line", DataType::UInt64, false),
    ];
    if optional.checkbox {
        fields.push(Field::new("checkbox_raw", DataType::Utf8, true));
        fields.push(Field::new("checkbox_state", DataType::Utf8, true));
    }
    if optional.leading_key {
        fields.push(Field::new("leading_key", DataType::Utf8, true));
    }
    if optional.relationship_kind {
        fields.push(Field::new("relationship_kind", DataType::Utf8, true));
    }
    Arc::new(Schema::new(fields))
}

fn list_item_column_names(optional: OptionalListColumns) -> Vec<&'static str> {
    let mut names = vec![
        "document_key",
        "ordinal",
        "section_ordinal",
        "parent_ordinal",
        "kind",
        "nesting_depth",
        "ordered_number",
        "raw_end_byte",
        "plain_text",
        "source_line",
        "start_byte",
        "end_byte",
        "start_line",
        "end_line",
    ];
    if optional.checkbox {
        names.extend(["checkbox_raw", "checkbox_state"]);
    }
    if optional.leading_key {
        names.push("leading_key");
    }
    if optional.relationship_kind {
        names.push("relationship_kind");
    }
    names
}

fn optional_columns(corpus: &MemoryCorpus) -> OptionalListColumns {
    let mut optional = OptionalListColumns::default();
    for document in &corpus.documents {
        let Some(parsed) = &document.parsed_markdown else {
            continue;
        };
        for item in &parsed.list_items {
            optional.checkbox |= item.checkbox.is_some();
            optional.leading_key |= item.leading_key.is_some();
            optional.relationship_kind |= item.relationship_kind.is_some();
        }
    }
    optional
}
