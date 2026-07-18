//! SQLite list-batch transaction behavior.

use rusqlite::Connection;

use crate::engine::helpers::publication::lists::test_types::MemoryListBatchFailureTestCase;
use crate::engine::helpers::publication::lists::{append_batch, ListItemRow};
use crate::markdown::models::{MarkdownListItem, SourceRange};
use crate::markdown::types::ListKind;

#[test]
fn given_second_row_trigger_failure_when_appending_batch_then_statement_is_atomic() {
    let test_cases = [MemoryListBatchFailureTestCase {
        description: "a trigger abort on the second row rolls back the complete SQLite statement",
        expected_error_fragment: "insert list item batch",
        expected_row_count: 0,
    }];
    for test_case in &test_cases {
        let mut connection = Connection::open_in_memory().expect("test database opens");
        connection
            .execute_batch(
                "CREATE TABLE _list_items (
                    document_key, ordinal, section_ordinal, parent_ordinal, kind,
                    nesting_depth, ordered_number, raw_end_byte, plain_text, source_line,
                    start_byte, end_byte, start_line, end_line, checkbox_raw, checkbox_state,
                    leading_key, relationship_kind
                );
                CREATE TRIGGER fail_second_list_item BEFORE INSERT ON _list_items
                WHEN NEW.ordinal = 1 BEGIN SELECT RAISE(ABORT, 'injected batch failure'); END;",
            )
            .expect("test schema is created");
        let source_range = SourceRange {
            start_byte: 0,
            end_byte: 6,
            start_line: 1,
            end_line: 1,
        };
        let items = [
            MarkdownListItem {
                ordinal: 0,
                kind: ListKind::Unordered,
                ordered_number: None,
                nesting_depth: 0,
                parent_ordinal: None,
                raw_markdown: "- first".to_owned(),
                plain_text: "first".to_owned(),
                source_line: 1,
                source_range: source_range.clone(),
                section_ordinal: None,
                checkbox: None,
                leading_key: None,
                relationship_kind: None,
            },
            MarkdownListItem {
                ordinal: 1,
                kind: ListKind::Unordered,
                ordered_number: None,
                nesting_depth: 0,
                parent_ordinal: None,
                raw_markdown: "- second".to_owned(),
                plain_text: "second".to_owned(),
                source_line: 2,
                source_range,
                section_ordinal: None,
                checkbox: None,
                leading_key: None,
                relationship_kind: None,
            },
        ];
        let rows = [
            ListItemRow {
                document_key: 0,
                item: &items[0],
            },
            ListItemRow {
                document_key: 0,
                item: &items[1],
            },
        ];
        let transaction = connection.transaction().expect("transaction begins");

        let error = append_batch(&transaction, &rows).expect_err("second row aborts the batch");
        let row_count: i64 = transaction
            .query_row("SELECT count(*) FROM _list_items", [], |row| row.get(0))
            .expect("failed batch remains queryable");

        assert!(
            error
                .to_string()
                .contains(test_case.expected_error_fragment),
            "{}: {error}",
            test_case.description
        );
        assert_eq!(
            row_count, test_case.expected_row_count,
            "{}",
            test_case.description
        );
        transaction.rollback().expect("test transaction rolls back");
    }
}
