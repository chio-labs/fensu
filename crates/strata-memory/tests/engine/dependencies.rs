//! Bundled SQLite and pure-Rust Git dependency behavior.

use std::path::Path;

use strata_memory::engine::main::probe_dependencies::probe_dependencies;

use crate::test_types;

#[path = "archive.rs"]
mod archive;
#[path = "check.rs"]
mod check;
#[path = "graph_query.rs"]
mod graph_query;
#[path = "helpers.rs"]
mod helpers;
#[path = "overview.rs"]
mod overview;
#[path = "performance.rs"]
mod performance;
#[path = "query.rs"]
mod query;
#[path = "schema.rs"]
mod schema;
#[path = "summary.rs"]
mod summary;
#[path = "sync.rs"]
mod sync;

#[test]
fn given_workspace_when_probing_dependencies_then_sqlite_and_git_are_available() {
    let test_cases = [test_types::DependencyProbeTestCase {
        description: "SQLite executes queries and Git parses repository excludes",
        expected_version_prefix: "3.",
    }];

    for test_case in &test_cases {
        let crate_root = Path::new(env!("CARGO_MANIFEST_DIR"));
        let workspace_root = crate_root
            .parent()
            .and_then(Path::parent)
            .expect("workspace root");
        let sqlite_version = probe_dependencies(workspace_root).expect("dependency probe");

        assert!(
            sqlite_version.starts_with(test_case.expected_version_prefix),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_canonical_memory_when_rebuilding_index_then_publishes_complete_replaceable_database() {
    let test_cases = [test_types::MemoryPublicationTestCase {
        description: "publishes valid and invalid memory facts through versioned tables and views",
        files: &[
            test_types::FixtureFile {
                path: ".ai/tasks/in-progress/20260717T120000_000000Z__FEAT-publish-index.md",
                contents: b"# Publish Index\n\nPreamble [site](https://example.com) #overview.\n\n## Phase 1: Build\n\n- [ ] Write schema #database\n- depends-on: [[task:20260717T115959_000000Z]]\n",
            },
            test_types::FixtureFile {
                path: ".ai/knowledge/repo/notes/20260717T120001_000000Z__NOTE-design-note.md",
                contents: b"# Design Note\n\nRemember this.\n",
            },
            test_types::FixtureFile {
                path: ".ai/knowledge/repo/notes/20260717T120002_000000Z__NOTE-invalid-note.md",
                contents: b"Document without a title.\n",
            },
            test_types::FixtureFile {
                path: ".ai/knowledge/repo/decisions/20260717T120003_000000Z__ADR-use-sqlite.md",
                contents: b"# Use SQLite\n\n## Context\n\nOffline publication.\n",
            },
            test_types::FixtureFile {
                path: ".ai/knowledge/repo/skills/indexer/SKILL.md",
                contents: b"# Indexer\n\nInstall instructions.\n",
            },
            test_types::FixtureFile {
                path: ".ai/knowledge/repo/skills/indexer/references/guide.txt",
                contents: b"support file\n",
            },
            test_types::FixtureFile {
                path: ".ai/orphan.md",
                contents: b"not canonical\n",
            },
        ],
        expected_table_names: &[
            "_document_keys",
            "_list_items",
            "documents",
            "links",
            "meta",
            "sections",
            "skill_files",
            "tags",
        ],
        expected_table_counts: &[5, 2, 5, 2, 1, 5, 1, 2],
        expected_view_names: &[
            "archived_tasks",
            "blocked_tasks",
            "broken_links",
            "checkboxes",
            "current_documents",
            "current_tasks",
            "decisions",
            "list_items",
            "notes",
            "relationships",
            "skills",
            "task_checkboxes",
            "task_dependencies",
            "task_phases",
            "tasks",
        ],
        expected_view_counts: &[0, 1, 1, 1, 5, 1, 1, 2, 2, 1, 1, 1, 1, 1, 1],
        expected_summary_counts: [5, 5, 2, 2, 2, 1, 1, 1, 1],
        expected_schema_versions: (3, 1),
        expected_invalid_row: ("invalid", 1, true, true, true),
        expected_preamble_row: (0, true, 2),
        expected_checkbox_row: (
            " ",
            "open",
            1,
            "unordered",
            "Publish Index > Phase 1: Build",
            "- [ ] Write schema #database",
        ),
        expected_relationship_row: ("depends-on", "unresolved", true, 1),
        expected_external_status: "external",
        expected_tag_rows: &[("database", 1), ("overview", 0)],
        expected_phase_row: ("phase", "1", "Build"),
        expected_skill_file_row: (false, true),
        expected_database_files: &["memory.sqlite3"],
    }];

    for test_case in &test_cases {
        helpers::run_case(test_case);
        assert_eq!(
            test_case.expected_table_names.len(),
            8,
            "{}",
            test_case.description
        );
    }
}
