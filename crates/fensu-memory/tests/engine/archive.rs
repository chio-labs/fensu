//! Explicit archive moves, confirmation, bundle ownership, and disabled automation.

use std::fs::{self, File, FileTimes};
use std::path::PathBuf;
#[cfg(any(unix, windows))]
use std::time::{Duration, SystemTime};

use fensu_memory::engine::main::archive_memory::archive_memory;
use fensu_memory::engine::main::sync_memory_index::sync_memory_index;
use rusqlite::Connection;

use crate::dependencies::helpers;
use crate::test_types::{
    FixtureFile, MemoryArchiveAutomaticTestCase, MemoryArchiveCtimeTestCase,
    MemoryArchiveTaskTestCase, MemoryArchiveTestCase,
};

#[test]
fn given_explicit_knowledge_when_archiving_then_moves_complete_source_and_synchronizes_index() {
    let test_cases = [
        MemoryArchiveTestCase {
            description: "archives one note without task confirmation",
            files: &[FixtureFile {
                path: ".ai/knowledge/repo/notes/20260717T120000_000000Z__NOTE-history.md",
                contents: b"# History\n",
            }],
            requested_path: ".ai/knowledge/repo/notes/20260717T120000_000000Z__NOTE-history.md",
            confirmed: false,
            expected_source_exists: false,
            expected_destination:
                ".ai/_archive/knowledge/repo/notes/20260717T120000_000000Z__NOTE-history.md",
            expected_move_count: 1,
        },
        MemoryArchiveTestCase {
            description: "archives one complete skill bundle from its bundle root",
            files: &[
                FixtureFile {
                    path: ".ai/knowledge/repo/skills/indexer/SKILL.md",
                    contents: b"# Indexer\n",
                },
                FixtureFile {
                    path: ".ai/knowledge/repo/skills/indexer/references/guide.txt",
                    contents: b"guide\n",
                },
            ],
            requested_path: ".ai/knowledge/repo/skills/indexer",
            confirmed: false,
            expected_source_exists: false,
            expected_destination: ".ai/_archive/knowledge/repo/skills/indexer",
            expected_move_count: 1,
        },
    ];
    for test_case in &test_cases {
        let root = helpers::write_repository(test_case.files);
        let database_path = root.join("memory.sqlite3");
        sync_memory_index(&root, &database_path).expect("initial sync succeeds");
        let result = archive_memory(
            &root,
            &database_path,
            &[PathBuf::from(test_case.requested_path)],
            7,
            test_case.confirmed,
        )
        .expect("knowledge archive succeeds");

        assert_eq!(result.moves.len(), test_case.expected_move_count);
        assert_eq!(
            root.join(test_case.requested_path).exists(),
            test_case.expected_source_exists,
            "{}",
            test_case.description
        );
        assert!(
            root.join(test_case.expected_destination).exists(),
            "{}",
            test_case.description
        );
        assert!(result.sync.is_some(), "{}", test_case.description);
        let connection = Connection::open(&database_path).expect("archive database opens");
        let archived: i64 = connection
            .query_row(
                "SELECT count(*) FROM documents WHERE archive_state = 'archived'",
                [],
                |row| row.get(0),
            )
            .expect("archived rows count");
        assert_eq!(archived, 1, "{}", test_case.description);
        connection.close().expect("archive database closes");
        fs::remove_dir_all(root).expect("archive repository is removable");
    }
}

#[test]
fn given_explicit_task_when_archiving_then_requires_terminal_lifecycle_and_confirmation() {
    let test_cases = [MemoryArchiveTaskTestCase {
        description: "requires confirmation and rejects nonterminal task lifecycle",
        files: &[
            FixtureFile {
                path: ".ai/tasks/completed/20260717T120001_000000Z__FEAT-done.md",
                contents: b"# Done\n",
            },
            FixtureFile {
                path: ".ai/tasks/in-progress/20260717T120002_000000Z__FEAT-active.md",
                contents: b"# Active\n",
            },
        ],
        completed_path: ".ai/tasks/completed/20260717T120001_000000Z__FEAT-done.md",
        active_path: ".ai/tasks/in-progress/20260717T120002_000000Z__FEAT-active.md",
        expected_confirmation_error: "requires --yes",
        expected_lifecycle_error: "must move to completed",
        expected_move_count: 1,
    }];
    for test_case in &test_cases {
        let root = helpers::write_repository(test_case.files);
        let database_path = root.join("memory.sqlite3");
        let completed = PathBuf::from(test_case.completed_path);
        let active = PathBuf::from(test_case.active_path);
        let confirmation = archive_memory(
            &root,
            &database_path,
            std::slice::from_ref(&completed),
            7,
            false,
        )
        .expect_err("explicit terminal task requires confirmation");
        assert!(
            confirmation
                .to_string()
                .contains(test_case.expected_confirmation_error),
            "{}",
            test_case.description
        );
        assert!(root.join(&completed).exists(), "{}", test_case.description);
        let lifecycle = archive_memory(
            &root,
            &database_path,
            std::slice::from_ref(&active),
            7,
            true,
        )
        .expect_err("active task cannot archive");
        assert!(
            lifecycle
                .to_string()
                .contains(test_case.expected_lifecycle_error),
            "{}",
            test_case.description
        );
        assert!(root.join(&active).exists(), "{}", test_case.description);
        let result = archive_memory(
            &root,
            &database_path,
            std::slice::from_ref(&completed),
            7,
            true,
        )
        .expect("confirmed terminal task archives");
        assert_eq!(
            result.moves.len(),
            test_case.expected_move_count,
            "{}",
            test_case.description
        );
        assert!(!root.join(completed).exists(), "{}", test_case.description);
        fs::remove_dir_all(root).expect("task archive repository is removable");
    }
}

#[test]
fn given_zero_automatic_age_when_archiving_then_moves_nothing_and_does_not_sync() {
    let test_cases = [MemoryArchiveAutomaticTestCase {
        description: "zero days disables automatic age-based archival",
        files: &[FixtureFile {
            path: ".ai/tasks/completed/20260717T120003_000000Z__FIX-terminal.md",
            contents: b"# Terminal\n",
        }],
        archive_after_days: 0,
        expected_move_count: 0,
        expected_sync: false,
        expected_database_exists: false,
    }];
    for test_case in &test_cases {
        let root = helpers::write_repository(test_case.files);
        let database_path = root.join("memory.sqlite3");
        let result = archive_memory(
            &root,
            &database_path,
            &[],
            test_case.archive_after_days,
            false,
        )
        .expect("disabled automatic archive succeeds");
        assert_eq!(
            result.moves.len(),
            test_case.expected_move_count,
            "{}",
            test_case.description
        );
        assert_eq!(
            result.sync.is_some(),
            test_case.expected_sync,
            "{}",
            test_case.description
        );
        assert_eq!(
            database_path.exists(),
            test_case.expected_database_exists,
            "{}",
            test_case.description
        );
        assert!(
            root.join(".ai/tasks/completed/20260717T120003_000000Z__FIX-terminal.md")
                .exists(),
            "{}",
            test_case.description
        );
        fs::remove_dir_all(root).expect("zero-age repository is removable");
    }
}

#[cfg(unix)]
#[test]
fn given_old_mtime_and_recent_ctime_when_archiving_then_terminal_task_receives_grace_period() {
    let test_cases = [MemoryArchiveCtimeTestCase {
        description: "uses the newer Unix ctime after a lifecycle move",
        file: FixtureFile {
            path: ".ai/tasks/completed/20260717T120004_000000Z__FIX-recently-moved.md",
            contents: b"# Recently moved\n",
        },
        archive_after_days: 7,
        old_mtime_days: 30,
        expected_move_count: 0,
    }];
    for test_case in &test_cases {
        let root = helpers::write_repository(std::slice::from_ref(&test_case.file));
        let database_path = root.join("memory.sqlite3");
        let source_path = root.join(test_case.file.path);
        let old_mtime = SystemTime::now()
            .checked_sub(Duration::from_secs(test_case.old_mtime_days * 86_400))
            .expect("fixture mtime is representable");
        File::options()
            .write(true)
            .open(&source_path)
            .expect("terminal task opens")
            .set_times(FileTimes::new().set_modified(old_mtime))
            .expect("terminal task mtime changes");

        let result = archive_memory(
            &root,
            &database_path,
            &[],
            test_case.archive_after_days,
            false,
        )
        .expect("automatic archive succeeds");

        assert_eq!(
            result.moves.len(),
            test_case.expected_move_count,
            "{}",
            test_case.description
        );
        assert!(source_path.exists(), "{}", test_case.description);
        assert!(result.sync.is_none(), "{}", test_case.description);
        fs::remove_dir_all(root).expect("ctime repository is removable");
    }
}

#[cfg(windows)]
#[test]
fn given_old_mtime_when_archiving_on_windows_then_terminal_task_is_eligible() {
    let test_cases = [MemoryArchiveCtimeTestCase {
        description: "uses mtime when Windows provides no Unix ctime",
        file: FixtureFile {
            path: ".ai/tasks/completed/20260717T120004_000000Z__FIX-old-windows-task.md",
            contents: b"# Old Windows Task\n",
        },
        archive_after_days: 7,
        old_mtime_days: 30,
        expected_move_count: 1,
    }];
    for test_case in &test_cases {
        let root = helpers::write_repository(std::slice::from_ref(&test_case.file));
        let database_path = root.join("memory.sqlite3");
        let source_path = root.join(test_case.file.path);
        let old_mtime = SystemTime::now()
            .checked_sub(Duration::from_secs(test_case.old_mtime_days * 86_400))
            .expect("fixture mtime is representable");
        File::options()
            .write(true)
            .open(&source_path)
            .expect("terminal task opens")
            .set_times(FileTimes::new().set_modified(old_mtime))
            .expect("terminal task mtime changes");

        let result = archive_memory(
            &root,
            &database_path,
            &[],
            test_case.archive_after_days,
            false,
        )
        .expect("automatic archive succeeds");

        assert_eq!(
            result.moves.len(),
            test_case.expected_move_count,
            "{}",
            test_case.description
        );
        assert!(!source_path.exists(), "{}", test_case.description);
        assert!(result.sync.is_some(), "{}", test_case.description);
        fs::remove_dir_all(root).expect("Windows mtime repository is removable");
    }
}
