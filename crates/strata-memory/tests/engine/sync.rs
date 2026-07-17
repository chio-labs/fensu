//! Source reconciliation, unchanged fast path, and recovery behavior.

use std::fs;

use duckdb::Connection;
use strata_memory::engine::main::sync_memory_index::sync_memory_index;

use crate::dependencies::helpers;
use crate::test_types::{FixtureFile, MemoryRecoveryTestCase, MemorySyncTestCase};

#[test]
fn given_canonical_sources_when_syncing_then_classifies_changes_and_skips_unchanged_write() {
    let test_cases = [MemorySyncTestCase {
        description: "classifies document and support-file changes without rewriting equality",
        files: &[
            FixtureFile {
                path: ".ai/knowledge/repo/notes/20260717T120001_000000Z__NOTE-sync.md",
                contents: b"# Sync\n\nOriginal.\n",
            },
            FixtureFile {
                path: ".ai/knowledge/repo/skills/indexer/SKILL.md",
                contents: b"# Indexer\n\nInstructions.\n",
            },
            FixtureFile {
                path: ".ai/knowledge/repo/skills/indexer/references/guide.txt",
                contents: b"guide\n",
            },
        ],
        expected_initial: (3, 0, 0, 0, 0, true, true),
        expected_unchanged: (0, 0, 0, 0, 3, false, false),
        expected_edit: (1, 2, true),
        expected_document_move: (1, 2),
        expected_support_move: (1, 2),
        expected_remove: (1, 2),
    }];
    for test_case in &test_cases {
        let root = helpers::write_repository(test_case.files);
        let database_path = root.join("memory.duckdb");
        let initial = sync_memory_index(&root, &database_path).expect("initial sync succeeds");
        let initial_counts = (
            initial.added_count,
            initial.changed_count,
            initial.moved_count,
            initial.removed_count,
            initial.unchanged_count,
            initial.rebuilt,
            initial.changed,
        );
        let initial_database = fs::read(&database_path).expect("published database is readable");
        assert_eq!(
            initial_counts, test_case.expected_initial,
            "{}",
            test_case.description
        );

        let unchanged = sync_memory_index(&root, &database_path).expect("unchanged sync succeeds");
        let unchanged_counts = (
            unchanged.added_count,
            unchanged.changed_count,
            unchanged.moved_count,
            unchanged.removed_count,
            unchanged.unchanged_count,
            unchanged.rebuilt,
            unchanged.changed,
        );
        assert_eq!(
            unchanged_counts, test_case.expected_unchanged,
            "{}",
            test_case.description
        );
        assert_eq!(
            fs::read(&database_path).expect("unchanged database is readable"),
            initial_database,
            "{}",
            test_case.description
        );

        let note = root.join(".ai/knowledge/repo/notes/20260717T120001_000000Z__NOTE-sync.md");
        fs::write(&note, b"# Sync\n\nChanged.\n").expect("note edit succeeds");
        let edited = sync_memory_index(&root, &database_path).expect("edited sync succeeds");
        assert_eq!(
            (edited.changed_count, edited.unchanged_count, edited.rebuilt),
            test_case.expected_edit,
            "{}",
            test_case.description
        );

        let moved_note =
            root.join(".ai/knowledge/repo/notes/20260717T120001_000000Z__NOTE-renamed-sync.md");
        fs::rename(&note, &moved_note).expect("note move succeeds");
        let moved_document =
            sync_memory_index(&root, &database_path).expect("document move sync succeeds");
        assert_eq!(
            (moved_document.moved_count, moved_document.unchanged_count),
            test_case.expected_document_move,
            "{}",
            test_case.description
        );

        let support = root.join(".ai/knowledge/repo/skills/indexer/references/guide.txt");
        let moved_support = root.join(".ai/knowledge/repo/skills/indexer/references/manual.txt");
        fs::rename(&support, &moved_support).expect("support-file move succeeds");
        let moved_file =
            sync_memory_index(&root, &database_path).expect("support move sync succeeds");
        assert_eq!(
            (moved_file.moved_count, moved_file.unchanged_count),
            test_case.expected_support_move,
            "{}",
            test_case.description
        );

        fs::remove_file(&moved_support).expect("support-file removal succeeds");
        let removed = sync_memory_index(&root, &database_path).expect("removal sync succeeds");
        assert_eq!(
            (removed.removed_count, removed.unchanged_count),
            test_case.expected_remove,
            "{}",
            test_case.description
        );
        fs::remove_dir_all(root).expect("sync repository is removable");
    }
}

#[test]
fn given_incompatible_or_corrupt_database_when_syncing_then_rebuilds_atomically() {
    let test_cases = [MemoryRecoveryTestCase {
        description: "schema mismatch and unreadable bytes produce healthy atomic replacements",
        files: &[FixtureFile {
            path: ".ai/knowledge/repo/notes/20260717T120001_000000Z__NOTE-recovery.md",
            contents: b"# Recovery\n\nHealthy.\n",
        }],
        expected_incompatible: (0, 1, true, false),
        expected_corrupt: (1, 0, true, true),
        expected_document_count: 1,
    }];
    for test_case in &test_cases {
        let root = helpers::write_repository(test_case.files);
        let database_path = root.join("memory.duckdb");
        sync_memory_index(&root, &database_path).expect("initial sync succeeds");
        let connection = Connection::open(&database_path).expect("database opens");
        connection
            .execute("UPDATE meta SET schema_version = 999", [])
            .expect("schema version changes");
        connection.close().expect("database closes");
        let incompatible =
            sync_memory_index(&root, &database_path).expect("schema rebuild succeeds");
        assert_eq!(
            (
                incompatible.added_count,
                incompatible.unchanged_count,
                incompatible.rebuilt,
                incompatible.changed
            ),
            test_case.expected_incompatible,
            "{}",
            test_case.description
        );

        fs::write(&database_path, b"not a duckdb database").expect("database corruption succeeds");
        let corrupt = sync_memory_index(&root, &database_path).expect("corrupt rebuild succeeds");
        assert_eq!(
            (
                corrupt.added_count,
                corrupt.unchanged_count,
                corrupt.rebuilt,
                corrupt.changed
            ),
            test_case.expected_corrupt,
            "{}",
            test_case.description
        );
        let connection = Connection::open(&database_path).expect("rebuilt database opens");
        let document_count: i64 = connection
            .query_row("SELECT count(*) FROM memory.documents", [], |row| {
                row.get(0)
            })
            .expect("rebuilt database is queryable");
        assert_eq!(
            document_count, test_case.expected_document_count,
            "{}",
            test_case.description
        );
        connection.close().expect("rebuilt database closes");
        fs::remove_dir_all(root).expect("recovery repository is removable");
    }
}
