//! Canonical source discovery and diagnostic behavior.

use std::time::UNIX_EPOCH;

use strata_memory::source::main::discover_memory::discover_memory;
use strata_memory::source::types::{ArchiveState, DiagnosticKind, GitTracking};

use crate::helpers;
use crate::test_types::{
    CanonicalDiscoveryTestCase, DiagnosticDiscoveryTestCase, ExpectedDiagnostic, FixtureDirectory,
    FixtureFile,
};

#[test]
fn given_every_canonical_location_when_discovering_then_returns_portable_sorted_sources() {
    let test_cases = [CanonicalDiscoveryTestCase {
        description: "discovers every active and archived artifact location with source metadata",
        directories: &[],
        files: &[
            FixtureFile {
                path: ".ai/tasks/superseded/20260717T120004_000000Z__CHORE-active-superseded.md",
                contents: "body\n",
            },
            FixtureFile {
                path: ".ai/knowledge/repo/skills/active-skill/assets/guide.txt",
                contents: "body\n",
            },
            FixtureFile {
                path: ".ai/tasks/not-started/20260717T120000_000000Z__SPIKE-active-not-started.md",
                contents: "body\n",
            },
            FixtureFile {
                path: ".ai/_archive/tasks/superseded/20260717T120007_000000Z__REFACTOR-archived-superseded.md",
                contents: "body\n",
            },
            FixtureFile {
                path: ".ai/knowledge/repo/decisions/20260717T120006_000000Z__ADR-active-decision.md",
                contents: "body\n",
            },
            FixtureFile {
                path: ".ai/tasks/in-progress/20260717T120001_000000Z__FIX-active-in-progress.md",
                contents: "body\n",
            },
            FixtureFile {
                path: ".ai/_archive/knowledge/repo/skills/archived-skill/SKILL.md",
                contents: "body\n",
            },
            FixtureFile {
                path: ".ai/tasks/completed/20260717T120002_000000Z__PERF-active-completed.md",
                contents: "body\n",
            },
            FixtureFile {
                path: ".ai/_archive/tasks/cancelled/20260717T120006_000000Z__FIX-archived-cancelled.md",
                contents: "body\n",
            },
            FixtureFile {
                path: ".ai/knowledge/repo/skills/active-skill/SKILL.md",
                contents: "body\n",
            },
            FixtureFile {
                path: ".ai/_archive/knowledge/repo/notes/20260717T120008_000000Z__NOTE-archived-note.md",
                contents: "body\n",
            },
            FixtureFile {
                path: ".ai/tasks/cancelled/20260717T120003_000000Z__FEAT-active-cancelled.md",
                contents: "body\n",
            },
            FixtureFile {
                path: ".ai/_archive/tasks/completed/20260717T120005_000000Z__FEAT-archived-completed.md",
                contents: "body\n",
            },
            FixtureFile {
                path: ".ai/knowledge/repo/notes/20260717T120005_000000Z__NOTE-active-note.md",
                contents: "body\n",
            },
            FixtureFile {
                path: ".ai/_archive/knowledge/repo/decisions/20260717T120009_000000Z__ADR-archived-decision.md",
                contents: "body\n",
            },
            FixtureFile {
                path: ".ai/_archive/knowledge/repo/skills/archived-skill/references/rules.txt",
                contents: "body\n",
            },
        ],
        expected_document_paths: &[
            ".ai/_archive/knowledge/repo/decisions/20260717T120009_000000Z__ADR-archived-decision.md",
            ".ai/_archive/knowledge/repo/notes/20260717T120008_000000Z__NOTE-archived-note.md",
            ".ai/_archive/knowledge/repo/skills/archived-skill/SKILL.md",
            ".ai/_archive/tasks/cancelled/20260717T120006_000000Z__FIX-archived-cancelled.md",
            ".ai/_archive/tasks/completed/20260717T120005_000000Z__FEAT-archived-completed.md",
            ".ai/_archive/tasks/superseded/20260717T120007_000000Z__REFACTOR-archived-superseded.md",
            ".ai/knowledge/repo/decisions/20260717T120006_000000Z__ADR-active-decision.md",
            ".ai/knowledge/repo/notes/20260717T120005_000000Z__NOTE-active-note.md",
            ".ai/knowledge/repo/skills/active-skill/SKILL.md",
            ".ai/tasks/cancelled/20260717T120003_000000Z__FEAT-active-cancelled.md",
            ".ai/tasks/completed/20260717T120002_000000Z__PERF-active-completed.md",
            ".ai/tasks/in-progress/20260717T120001_000000Z__FIX-active-in-progress.md",
            ".ai/tasks/not-started/20260717T120000_000000Z__SPIKE-active-not-started.md",
            ".ai/tasks/superseded/20260717T120004_000000Z__CHORE-active-superseded.md",
        ],
        expected_skill_file_paths: &[
            ".ai/_archive/knowledge/repo/skills/archived-skill/references/rules.txt",
            ".ai/knowledge/repo/skills/active-skill/assets/guide.txt",
        ],
        expected_content_hash: "9e2ec912af5dff2a72300863864fc4da04e81999339d9fac5c7590ba8a3f4e11",
        expected_byte_size: 5,
        expected_mtime_after_epoch: true,
        expected_change_time: cfg!(unix),
        expected_archived_document_count: 6,
        expected_archived_skill_file_count: 1,
    }];

    for test_case in &test_cases {
        let root = helpers::write_temp_tree(test_case.directories, test_case.files);
        let result = discover_memory(&root);
        let metadata_valid = result.documents.iter().all(|document| {
            document.metadata.content_sha256 == test_case.expected_content_hash
                && document.metadata.byte_size == test_case.expected_byte_size
                && document.git_tracking == GitTracking::Unavailable
        });
        let mtime_after_epoch = result
            .documents
            .iter()
            .all(|document| document.metadata.modified_at > UNIX_EPOCH);
        let change_time_present = result
            .documents
            .iter()
            .all(|document| document.metadata.changed_at.is_some());
        let archived_document_count = result
            .documents
            .iter()
            .filter(|document| document.canonical_path.archive_state == ArchiveState::Archived)
            .count();
        let archived_skill_file_count = result
            .skill_files
            .iter()
            .filter(|file| file.canonical_path.archive_state == ArchiveState::Archived)
            .count();

        assert_eq!(
            helpers::document_paths(&result),
            test_case.expected_document_paths,
            "{}",
            test_case.description
        );
        assert_eq!(
            helpers::skill_file_paths(&result),
            test_case.expected_skill_file_paths,
            "{}",
            test_case.description
        );
        assert!(metadata_valid, "{}", test_case.description);
        assert_eq!(
            mtime_after_epoch, test_case.expected_mtime_after_epoch,
            "{}",
            test_case.description
        );
        assert_eq!(
            change_time_present, test_case.expected_change_time,
            "{}",
            test_case.description
        );
        assert_eq!(
            archived_document_count, test_case.expected_archived_document_count,
            "{}",
            test_case.description
        );
        assert_eq!(
            archived_skill_file_count, test_case.expected_archived_skill_file_count,
            "{}",
            test_case.description
        );
        helpers::remove_temp_tree(&root);
    }
}

#[test]
fn given_malformed_and_unknown_entries_when_discovering_then_collects_all_diagnostics() {
    let test_cases = [DiagnosticDiscoveryTestCase {
        description: "rejects malformed timestamps, names, root Markdown, and unknown structure",
        directories: &[
            FixtureDirectory {
                path: ".ai/mystery",
            },
            FixtureDirectory {
                path: ".ai/tasks/wrong-state",
            },
            FixtureDirectory {
                path: ".ai/knowledge/unknown",
            },
            FixtureDirectory {
                path: ".ai/knowledge/repo/skills/Bad-Skill",
            },
            FixtureDirectory {
                path: ".ai/knowledge/repo/skills/con",
            },
        ],
        files: &[
            FixtureFile {
                path: ".ai/root.md",
                contents: "body\n",
            },
            FixtureFile {
                path: ".ai/tasks/not-started/20260230T120000_000000Z__FEAT-bad-date.md",
                contents: "body\n",
            },
            FixtureFile {
                path: ".ai/tasks/not-started/20260717T120000_000000Z__BUG-wrong-category.md",
                contents: "body\n",
            },
            FixtureFile {
                path: ".ai/tasks/not-started/20260717T120000_000000Z__FIX-Bad-slug.md",
                contents: "body\n",
            },
            FixtureFile {
                path: ".ai/tasks/not-started/20260717T120000_00000Z__FEAT-short-fraction.md",
                contents: "body\n",
            },
            FixtureFile {
                path: ".ai/knowledge/repo/notes/20260717T120000_000000Z__MEMO-wrong-prefix.md",
                contents: "body\n",
            },
            FixtureFile {
                path: ".ai/knowledge/repo/decisions/20261317T120000_000000Z__ADR-bad-month.md",
                contents: "body\n",
            },
            FixtureFile {
                path: ".ai/knowledge/repo/random.md",
                contents: "body\n",
            },
        ],
        expected_document_count: 0,
        expected_diagnostics: &[
            ExpectedDiagnostic {
                path: ".ai/knowledge/repo/decisions/20261317T120000_000000Z__ADR-bad-month.md",
                kind: DiagnosticKind::InvalidTimestamp,
            },
            ExpectedDiagnostic {
                path: ".ai/knowledge/repo/notes/20260717T120000_000000Z__MEMO-wrong-prefix.md",
                kind: DiagnosticKind::InvalidArtifactPrefix,
            },
            ExpectedDiagnostic {
                path: ".ai/knowledge/repo/random.md",
                kind: DiagnosticKind::UnknownStructuralEntry,
            },
            ExpectedDiagnostic {
                path: ".ai/knowledge/repo/skills/Bad-Skill",
                kind: DiagnosticKind::InvalidSlug,
            },
            ExpectedDiagnostic {
                path: ".ai/knowledge/repo/skills/con",
                kind: DiagnosticKind::InvalidPlatformName,
            },
            ExpectedDiagnostic {
                path: ".ai/knowledge/unknown",
                kind: DiagnosticKind::UnknownStructuralEntry,
            },
            ExpectedDiagnostic {
                path: ".ai/mystery",
                kind: DiagnosticKind::UnknownStructuralEntry,
            },
            ExpectedDiagnostic {
                path: ".ai/root.md",
                kind: DiagnosticKind::RootMarkdown,
            },
            ExpectedDiagnostic {
                path: ".ai/tasks/not-started/20260230T120000_000000Z__FEAT-bad-date.md",
                kind: DiagnosticKind::InvalidTimestamp,
            },
            ExpectedDiagnostic {
                path: ".ai/tasks/not-started/20260717T120000_000000Z__BUG-wrong-category.md",
                kind: DiagnosticKind::InvalidTaskCategory,
            },
            ExpectedDiagnostic {
                path: ".ai/tasks/not-started/20260717T120000_000000Z__FIX-Bad-slug.md",
                kind: DiagnosticKind::InvalidSlug,
            },
            ExpectedDiagnostic {
                path: ".ai/tasks/not-started/20260717T120000_00000Z__FEAT-short-fraction.md",
                kind: DiagnosticKind::InvalidTimestamp,
            },
            ExpectedDiagnostic {
                path: ".ai/tasks/wrong-state",
                kind: DiagnosticKind::UnknownStructuralEntry,
            },
        ],
    }];

    for test_case in &test_cases {
        let root = helpers::write_temp_tree(test_case.directories, test_case.files);
        let result = discover_memory(&root);
        let expected: Vec<(&str, DiagnosticKind)> = test_case
            .expected_diagnostics
            .iter()
            .map(|diagnostic| (diagnostic.path, diagnostic.kind))
            .collect();

        assert_eq!(
            result.documents.len(),
            test_case.expected_document_count,
            "{}",
            test_case.description
        );
        assert_eq!(
            helpers::diagnostic_rows(&result),
            expected,
            "{}",
            test_case.description
        );
        helpers::remove_temp_tree(&root);
    }
}
