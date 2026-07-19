//! Multi-chunk graph parity and late-diagnostic rollback behavior.

use std::fs;

use fensu_memory::engine::main::check_memory::check_memory;
use fensu_memory::engine::main::rebuild_memory_index::rebuild_memory_index;
use fensu_memory::engine::main::sync_memory_index::sync_memory_index;
use rusqlite::Connection;

use crate::dependencies::{helpers, streaming_helpers};
use crate::test_types::{FixtureFile, MemoryStreamingFailureTestCase, MemoryStreamingTestCase};

#[test]
fn given_cross_chunk_relationship_cycle_when_rebuilding_then_resolves_complete_graph() {
    let test_cases = [MemoryStreamingTestCase {
        description: "resolves links and cycles across the publication chunk boundary",
        document_count: 513,
        expected_document_count: 513,
        expected_list_item_count: 2,
        expected_max_loaded_documents: 512,
        expected_link_count: 2,
        expected_graph_diagnostic_count: 1,
        expected_late_diagnostic_count: 0,
    }];
    for test_case in &test_cases {
        let root = helpers::write_repository(&[]);
        streaming_helpers::write_cross_chunk_cycle(&root, test_case.document_count);
        let database_path = root.join("memory.sqlite3");

        let summary = rebuild_memory_index(&root, &database_path).expect("streaming rebuild works");

        assert_eq!(
            summary.document_count, test_case.expected_document_count,
            "{}",
            test_case.description
        );
        assert_eq!(
            summary.list_item_count, test_case.expected_list_item_count,
            "{}",
            test_case.description
        );
        assert_eq!(
            summary.max_loaded_document_batch, test_case.expected_max_loaded_documents,
            "{}",
            test_case.description
        );
        assert_eq!(
            summary.link_count, test_case.expected_link_count,
            "{}",
            test_case.description
        );
        assert_eq!(
            summary.graph_diagnostic_count, test_case.expected_graph_diagnostic_count,
            "{}",
            test_case.description
        );
        let connection = Connection::open(&database_path).expect("streaming database opens");
        let resolved_count: i64 = connection
            .query_row(
                "SELECT count(*) FROM links WHERE resolution_status = 'resolved'",
                [],
                |row| row.get(0),
            )
            .expect("cross-chunk links are queryable");
        assert_eq!(
            resolved_count as usize, test_case.expected_link_count,
            "{}",
            test_case.description
        );
        connection.close().expect("streaming database closes");
        fs::remove_dir_all(root).expect("streaming repository is removable");
    }
}

#[test]
fn given_invalid_document_in_final_chunk_when_checking_then_preserves_prior_database() {
    let test_cases = [MemoryStreamingTestCase {
        description: "rolls back all streamed rows when the final chunk is invalid",
        document_count: 513,
        expected_document_count: 513,
        expected_list_item_count: 0,
        expected_max_loaded_documents: 512,
        expected_link_count: 0,
        expected_graph_diagnostic_count: 0,
        expected_late_diagnostic_count: 1,
    }];
    for test_case in &test_cases {
        let root = helpers::write_repository(&[FixtureFile {
            path: ".ai/knowledge/repo/notes/20260718T150000_000000Z__NOTE-streaming-0.md",
            contents: b"# Existing\n",
        }]);
        let database_path = root.join("memory.sqlite3");
        sync_memory_index(&root, &database_path).expect("prior database publishes");
        let prior = fs::read(&database_path).expect("prior database is readable");
        streaming_helpers::write_late_invalid_documents(&root, test_case.document_count);

        let result = check_memory(&root, &database_path).expect("streaming check completes");

        assert_eq!(
            result.diagnostics.len(),
            test_case.expected_late_diagnostic_count,
            "{}",
            test_case.description
        );
        assert!(result.published.is_none(), "{}", test_case.description);
        assert_eq!(
            fs::read(&database_path).expect("prior database remains readable"),
            prior,
            "{}",
            test_case.description
        );
        fs::remove_dir_all(root).expect("streaming repository is removable");
    }
}

#[test]
fn given_sqlite_failure_in_final_chunk_when_rebuilding_then_preserves_prior_database_and_cleans() {
    let test_cases = [MemoryStreamingFailureTestCase {
        description: "removes streamed temporary files after a late unique-key failure",
        document_count: 513,
        expected_error_fragment: "insert document",
        expected_temporary_count: 0,
    }];
    for test_case in &test_cases {
        let root = helpers::write_repository(&[FixtureFile {
            path: ".ai/knowledge/repo/notes/20260718T155000_000000Z__NOTE-prior.md",
            contents: b"# Prior\n",
        }]);
        let database_path = root.join("memory.sqlite3");
        sync_memory_index(&root, &database_path).expect("prior database publishes");
        let prior = fs::read(&database_path).expect("prior database is readable");
        streaming_helpers::write_late_identity_collision(&root, test_case.document_count);

        let error = rebuild_memory_index(&root, &database_path)
            .expect_err("late SQLite identity collision fails publication");
        let temporary_count = fs::read_dir(&root)
            .expect("streaming repository root is readable")
            .filter_map(Result::ok)
            .filter(|entry| {
                entry
                    .file_name()
                    .to_string_lossy()
                    .contains(".fensu-memory-")
            })
            .count();

        assert!(
            error
                .to_string()
                .contains(test_case.expected_error_fragment),
            "{}: {error}",
            test_case.description
        );
        assert_eq!(
            fs::read(&database_path).expect("prior database remains readable"),
            prior,
            "{}",
            test_case.description
        );
        assert_eq!(
            temporary_count, test_case.expected_temporary_count,
            "{}",
            test_case.description
        );
        fs::remove_dir_all(root).expect("streaming failure repository is removable");
    }
}
