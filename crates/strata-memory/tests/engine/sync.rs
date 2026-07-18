//! Source reconciliation, unchanged fast path, and recovery behavior.

use std::fs;
#[cfg(unix)]
use std::os::unix::fs::PermissionsExt;
#[cfg(unix)]
use std::thread;

use rusqlite::{Connection, OpenFlags};
use strata_memory::engine::main::sync_memory_index::sync_memory_index;

use crate::dependencies::helpers;
use crate::test_types::{
    FixtureFile, MemoryConcurrentPublicationTestCase, MemoryPermissionFailureTestCase,
    MemoryRecoveryTestCase, MemorySyncTestCase,
};

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
        let database_path = root.join("memory.sqlite3");
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
        let database_path = root.join("memory.sqlite3");
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

        fs::write(&database_path, b"not a sqlite database").expect("database corruption succeeds");
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
            .query_row("SELECT count(*) FROM documents", [], |row| row.get(0))
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

#[cfg(unix)]
#[test]
fn given_reader_and_concurrent_writers_when_syncing_then_every_generation_remains_complete() {
    let test_cases = [MemoryConcurrentPublicationTestCase {
        description: "keeps an open reader on the prior generation while two writers publish",
        files: &[FixtureFile {
            path: ".ai/knowledge/repo/notes/20260717T120001_000000Z__NOTE-first.md",
            contents: b"# First\n",
        }],
        added_file: FixtureFile {
            path: ".ai/knowledge/repo/notes/20260717T120002_000000Z__NOTE-second.md",
            contents: b"# Second\n",
        },
        expected_reader_document_count: 1,
        expected_published_document_count: 2,
    }];
    for test_case in &test_cases {
        let root = helpers::write_repository(test_case.files);
        let database_path = root.join("memory.sqlite3");
        sync_memory_index(&root, &database_path).expect("initial sync succeeds");
        let reader = Connection::open_with_flags(&database_path, OpenFlags::SQLITE_OPEN_READ_ONLY)
            .expect("prior generation opens read-only");
        let added_path = root.join(test_case.added_file.path);
        fs::write(&added_path, test_case.added_file.contents).expect("second note is writable");
        let first_root = root.clone();
        let first_database = database_path.clone();
        let second_root = root.clone();
        let second_database = database_path.clone();

        let first_writer = thread::spawn(move || sync_memory_index(&first_root, &first_database));
        let second_writer =
            thread::spawn(move || sync_memory_index(&second_root, &second_database));
        first_writer
            .join()
            .expect("first writer does not panic")
            .expect("first writer succeeds");
        second_writer
            .join()
            .expect("second writer does not panic")
            .expect("second writer succeeds");

        let reader_count: i64 = reader
            .query_row("SELECT count(*) FROM documents", [], |row| row.get(0))
            .expect("prior generation remains queryable");
        assert_eq!(
            reader_count, test_case.expected_reader_document_count,
            "{}",
            test_case.description
        );
        reader.close().expect("prior generation reader closes");
        let published = Connection::open(&database_path).expect("published generation opens");
        let published_count: i64 = published
            .query_row("SELECT count(*) FROM documents", [], |row| row.get(0))
            .expect("published generation is complete");
        assert_eq!(
            published_count, test_case.expected_published_document_count,
            "{}",
            test_case.description
        );
        published.close().expect("published generation closes");
        let temporary_count = fs::read_dir(&root)
            .expect("repository root is readable")
            .filter_map(Result::ok)
            .filter(|entry| {
                entry
                    .file_name()
                    .to_string_lossy()
                    .contains(".strata-memory-")
            })
            .count();
        assert_eq!(temporary_count, 0, "{}", test_case.description);
        fs::remove_dir_all(root).expect("concurrent repository is removable");
    }
}

#[cfg(unix)]
#[test]
fn given_denied_database_directory_when_syncing_then_prior_generation_is_preserved() {
    let test_cases = [MemoryPermissionFailureTestCase {
        description: "leaves prior bytes intact and removes no valid index on permission failure",
        files: &[FixtureFile {
            path: ".ai/knowledge/repo/notes/20260717T120001_000000Z__NOTE-permission.md",
            contents: b"# Permission\n\nOriginal.\n",
        }],
        changed_contents: b"# Permission\n\nChanged.\n",
        expected_error_fragment: "temporary memory index",
    }];
    for test_case in &test_cases {
        let root = helpers::write_repository(test_case.files);
        let database_path = root.join("memory.sqlite3");
        sync_memory_index(&root, &database_path).expect("initial sync succeeds");
        let original_database = fs::read(&database_path).expect("prior database is readable");
        fs::write(
            root.join(test_case.files[0].path),
            test_case.changed_contents,
        )
        .expect("source edit succeeds");
        let original_permissions = fs::metadata(&root)
            .expect("repository metadata is readable")
            .permissions();
        fs::set_permissions(&root, fs::Permissions::from_mode(0o500))
            .expect("repository publication can be denied");

        let result = sync_memory_index(&root, &database_path);

        fs::set_permissions(&root, original_permissions).expect("repository permissions restore");
        let error = result.expect_err("publication without directory write permission fails");
        assert!(
            error
                .to_string()
                .contains(test_case.expected_error_fragment),
            "{}: {error}",
            test_case.description
        );
        assert_eq!(
            fs::read(&database_path).expect("prior database remains readable"),
            original_database,
            "{}",
            test_case.description
        );
        let temporary_count = fs::read_dir(&root)
            .expect("repository root is readable")
            .filter_map(Result::ok)
            .filter(|entry| {
                entry
                    .file_name()
                    .to_string_lossy()
                    .contains(".strata-memory-")
            })
            .count();
        assert_eq!(temporary_count, 0, "{}", test_case.description);
        fs::remove_dir_all(root).expect("permission repository is removable");
    }
}
