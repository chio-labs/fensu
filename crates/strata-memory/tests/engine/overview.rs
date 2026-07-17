//! Read-only post-sync overview behavior.

use std::fs;

use strata_memory::engine::main::memory_overview::memory_overview;
use strata_memory::engine::main::sync_memory_index::sync_memory_index;

use crate::dependencies::helpers;
use crate::test_types::{FixtureFile, MemoryOverviewTestCase};

#[test]
fn given_synchronized_lifecycle_and_archive_sources_when_reading_overview_then_returns_all_counts()
{
    let test_cases = [MemoryOverviewTestCase {
        description: "counts every active lifecycle and archived artifact family",
        files: &[
            FixtureFile {
                path: ".ai/tasks/not-started/20260717T120001_000000Z__FEAT-one.md",
                contents: b"# One\n\nBody.\n",
            },
            FixtureFile {
                path: ".ai/tasks/in-progress/20260717T120002_000000Z__FIX-two.md",
                contents: b"# Two\n\nBody.\n",
            },
            FixtureFile {
                path: ".ai/tasks/completed/20260717T120003_000000Z__CHORE-three.md",
                contents: b"# Three\n\nBody.\n",
            },
            FixtureFile {
                path: ".ai/tasks/cancelled/20260717T120004_000000Z__SPIKE-four.md",
                contents: b"# Four\n\nBody.\n",
            },
            FixtureFile {
                path: ".ai/tasks/superseded/20260717T120005_000000Z__PERF-five.md",
                contents: b"# Five\n\nBody.\n",
            },
            FixtureFile {
                path: ".ai/knowledge/repo/notes/20260717T120006_000000Z__NOTE-six.md",
                contents: b"# Six\n\nBody.\n",
            },
            FixtureFile {
                path: ".ai/knowledge/repo/decisions/20260717T120007_000000Z__ADR-seven.md",
                contents: b"# Seven\n\nBody.\n",
            },
            FixtureFile {
                path: ".ai/knowledge/repo/skills/eight/SKILL.md",
                contents: b"# Eight\n\nBody.\n",
            },
            FixtureFile {
                path: ".ai/_archive/tasks/completed/20260717T120009_000000Z__FEAT-nine.md",
                contents: b"# Nine\n\nBody.\n",
            },
            FixtureFile {
                path: ".ai/_archive/knowledge/repo/notes/20260717T120010_000000Z__NOTE-ten.md",
                contents: b"# Ten\n\nBody.\n",
            },
        ],
        expected_counts: (1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 10, 10),
    }];
    for test_case in &test_cases {
        let root = helpers::write_repository(test_case.files);
        let database_path = root.join("memory.duckdb");
        sync_memory_index(&root, &database_path).expect("overview sync succeeds");
        let overview = memory_overview(&database_path).expect("overview succeeds");
        assert_eq!(
            (
                overview.not_started_task_count,
                overview.in_progress_task_count,
                overview.completed_task_count,
                overview.cancelled_task_count,
                overview.superseded_task_count,
                overview.active_note_count,
                overview.active_decision_count,
                overview.active_skill_count,
                overview.archived_task_count,
                overview.archived_knowledge_count,
                overview.document_count,
                overview.section_count,
            ),
            test_case.expected_counts,
            "{}",
            test_case.description
        );
        fs::remove_dir_all(root).expect("overview repository is removable");
    }
}
