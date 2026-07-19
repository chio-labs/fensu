//! Read-only bounded SQLite query behavior.

use std::fs;

use fensu_memory::engine::main::query_memory_index::query_memory_index;
use fensu_memory::engine::models::MemoryQueryValue;

use crate::dependencies::helpers;
use crate::test_types::{InvalidMemoryQueryTestCase, MemoryQueryTestCase};

#[test]
fn given_supported_sqlite_values_when_querying_then_returns_owned_tagged_values() {
    let test_cases = [MemoryQueryTestCase {
        description: "returns every SQLite storage class with stable public values",
        sql: "SELECT NULL AS null_value, 42 AS int_value, 1.5 AS real_value, 'text' AS text_value, X'00FF' AS blob_value;",
        limit: 10,
        expected_columns: &[
            "null_value",
            "int_value",
            "real_value",
            "text_value",
            "blob_value",
        ],
        expected_types: &["Null", "Integer", "Real", "Text", "Blob"],
        expected_row_count: 1,
        expected_truncated: false,
    }];

    for test_case in &test_cases {
        let (root, database_path) = helpers::write_query_database();
        let result = query_memory_index(&database_path, test_case.sql, test_case.limit)
            .expect("supported query succeeds");
        let expected_row = vec![
            MemoryQueryValue::Null,
            MemoryQueryValue::Integer("42".to_owned()),
            MemoryQueryValue::Float(1.5),
            MemoryQueryValue::String("text".to_owned()),
            MemoryQueryValue::Object(vec![
                (
                    "$type".to_owned(),
                    MemoryQueryValue::String("blob".to_owned()),
                ),
                (
                    "hex".to_owned(),
                    MemoryQueryValue::String("00ff".to_owned()),
                ),
            ]),
        ];

        assert_eq!(
            result.columns, test_case.expected_columns,
            "{}: column names",
            test_case.description
        );
        assert_eq!(
            result.types, test_case.expected_types,
            "{}: logical types",
            test_case.description
        );
        assert_eq!(
            result.rows.len(),
            test_case.expected_row_count,
            "{}: row count",
            test_case.description
        );
        assert_eq!(
            result.truncated, test_case.expected_truncated,
            "{}: truncation state",
            test_case.description
        );
        assert_eq!(result.rows[0], expected_row, "{}", test_case.description);
        fs::remove_dir_all(root).expect("query repository is removable");
    }
}

#[test]
fn given_more_rows_than_limit_when_querying_then_returns_limit_and_truncation() {
    let test_cases = [MemoryQueryTestCase {
        description: "uses one sentinel row to report truncation",
        sql: "SELECT column1 AS value FROM (VALUES (0), (1), (2), (3), (4))",
        limit: 2,
        expected_columns: &["value"],
        expected_types: &["Integer"],
        expected_row_count: 2,
        expected_truncated: true,
    }];

    for test_case in &test_cases {
        let (root, database_path) = helpers::write_query_database();
        let result = query_memory_index(&database_path, test_case.sql, test_case.limit)
            .expect("bounded query succeeds");

        assert_eq!(
            result.rows.len(),
            test_case.expected_row_count,
            "{}: bounded rows",
            test_case.description
        );
        assert_eq!(
            result.truncated, test_case.expected_truncated,
            "{}: truncation marker",
            test_case.description
        );
        assert_eq!(
            result.rows[1][0],
            MemoryQueryValue::Integer("1".to_owned()),
            "{}: row order",
            test_case.description
        );
        fs::remove_dir_all(root).expect("query repository is removable");
    }
}

#[test]
fn given_invalid_inputs_when_querying_then_returns_actionable_errors() {
    let test_cases = [
        InvalidMemoryQueryTestCase {
            description: "rejects a zero row limit",
            sql: "SELECT 1",
            limit: 0,
            expected_error_fragment: "limit 0 is invalid",
        },
        InvalidMemoryQueryTestCase {
            description: "rejects a row limit above the maximum",
            sql: "SELECT 1",
            limit: 1001,
            expected_error_fragment: "limit 1001 is invalid",
        },
        InvalidMemoryQueryTestCase {
            description: "rejects an empty query after its trailing semicolon",
            sql: " ; ",
            limit: 1,
            expected_error_fragment: "query is empty",
        },
    ];

    for test_case in &test_cases {
        let (root, database_path) = helpers::write_query_database();
        let error = query_memory_index(&database_path, test_case.sql, test_case.limit)
            .expect_err("invalid query fails");

        assert!(
            error
                .to_string()
                .contains(test_case.expected_error_fragment),
            "{}: {error}",
            test_case.description
        );
        fs::remove_dir_all(root).expect("query repository is removable");
    }
}

#[test]
fn given_mutating_or_multiple_statements_when_querying_then_database_is_unchanged() {
    let test_cases = [
        InvalidMemoryQueryTestCase {
            description: "rejects data mutation inside the query wrapper",
            sql: "DELETE FROM memory.sentinel",
            limit: 10,
            expected_error_fragment: "prepare read-only memory query",
        },
        InvalidMemoryQueryTestCase {
            description: "rejects a second statement inside the query wrapper",
            sql: "SELECT * FROM memory.sentinel; DELETE FROM memory.sentinel",
            limit: 10,
            expected_error_fragment: "prepare read-only memory query",
        },
    ];
    let (root, database_path) = helpers::write_query_database();

    for test_case in &test_cases {
        let error = query_memory_index(&database_path, test_case.sql, test_case.limit)
            .expect_err("unsafe query fails");

        assert!(
            error
                .to_string()
                .contains(test_case.expected_error_fragment),
            "{}: {error}",
            test_case.description
        );
        assert_eq!(
            helpers::sentinel_count(&database_path),
            1,
            "{}: database contents",
            test_case.description
        );
    }
    fs::remove_dir_all(root).expect("query repository is removable");
}

#[test]
fn given_external_file_reader_when_querying_then_external_access_is_rejected() {
    let test_cases = [InvalidMemoryQueryTestCase {
        description: "exposes no SQLite function for external file reads",
        sql: "SELECT * FROM read_csv('/etc/passwd')",
        limit: 10,
        expected_error_fragment: "read-only memory query",
    }];

    for test_case in &test_cases {
        let (root, database_path) = helpers::write_query_database();
        let error = query_memory_index(&database_path, test_case.sql, test_case.limit)
            .expect_err("external query fails");

        assert!(
            error
                .to_string()
                .contains(test_case.expected_error_fragment),
            "{}: {error}",
            test_case.description
        );
        assert_eq!(
            helpers::sentinel_count(&database_path),
            1,
            "{}: database contents",
            test_case.description
        );
        fs::remove_dir_all(root).expect("query repository is removable");
    }
}

#[test]
fn given_missing_database_when_querying_then_returns_error_without_creating_file() {
    let test_cases = [InvalidMemoryQueryTestCase {
        description: "reports the missing index path without opening it",
        sql: "SELECT 1",
        limit: 1,
        expected_error_fragment: "does not exist",
    }];

    for test_case in &test_cases {
        let root = helpers::write_repository(&[]);
        let database_path = root.join("missing.sqlite3");
        let error = query_memory_index(&database_path, test_case.sql, test_case.limit)
            .expect_err("missing database fails");

        assert!(
            error
                .to_string()
                .contains(test_case.expected_error_fragment),
            "{}: {error}",
            test_case.description
        );
        assert!(!database_path.exists(), "{}", test_case.description);
        fs::remove_dir_all(root).expect("query repository is removable");
    }
}
