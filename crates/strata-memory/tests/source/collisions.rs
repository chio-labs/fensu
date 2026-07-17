//! Deterministic duplicate and case-fold collision diagnostics.

use strata_memory::source::main::discover_memory::discover_memory;
use strata_memory::source::types::DiagnosticKind;

use crate::helpers;
use crate::test_types::{CollisionDiscoveryTestCase, ExpectedDiagnostic, FixtureFile};

#[test]
fn given_duplicate_and_case_colliding_sources_when_discovering_then_reports_sorted_collisions() {
    let test_cases = [CollisionDiscoveryTestCase {
        description: "sorts sources and reports duplicate task identity and skill file case folds",
        files: &[
            FixtureFile {
                path: ".ai/knowledge/repo/skills/collision-skill/guide.txt",
                contents: "lower\n",
            },
            FixtureFile {
                path: ".ai/tasks/not-started/20260717T120000_000000Z__FEAT-duplicate.md",
                contents: "active\n",
            },
            FixtureFile {
                path: ".ai/knowledge/repo/skills/collision-skill/SKILL.md",
                contents: "skill\n",
            },
            FixtureFile {
                path: ".ai/_archive/tasks/completed/20260717T120000_000000Z__FEAT-duplicate.md",
                contents: "archive\n",
            },
            FixtureFile {
                path: ".ai/knowledge/repo/skills/collision-skill/Guide.txt",
                contents: "upper\n",
            },
        ],
        expected_document_paths: &[
            ".ai/_archive/tasks/completed/20260717T120000_000000Z__FEAT-duplicate.md",
            ".ai/knowledge/repo/skills/collision-skill/SKILL.md",
            ".ai/tasks/not-started/20260717T120000_000000Z__FEAT-duplicate.md",
        ],
        expected_skill_file_paths: &[
            ".ai/knowledge/repo/skills/collision-skill/Guide.txt",
            ".ai/knowledge/repo/skills/collision-skill/guide.txt",
        ],
        expected_diagnostics: &[
            ExpectedDiagnostic {
                path: ".ai/_archive/tasks/completed/20260717T120000_000000Z__FEAT-duplicate.md",
                kind: DiagnosticKind::DuplicateIdentity,
            },
            ExpectedDiagnostic {
                path: ".ai/_archive/tasks/completed/20260717T120000_000000Z__FEAT-duplicate.md",
                kind: DiagnosticKind::DuplicateBasename,
            },
            ExpectedDiagnostic {
                path: ".ai/knowledge/repo/skills/collision-skill/Guide.txt",
                kind: DiagnosticKind::CaseFoldCollision,
            },
            ExpectedDiagnostic {
                path: ".ai/knowledge/repo/skills/collision-skill/guide.txt",
                kind: DiagnosticKind::CaseFoldCollision,
            },
            ExpectedDiagnostic {
                path: ".ai/tasks/not-started/20260717T120000_000000Z__FEAT-duplicate.md",
                kind: DiagnosticKind::DuplicateIdentity,
            },
            ExpectedDiagnostic {
                path: ".ai/tasks/not-started/20260717T120000_000000Z__FEAT-duplicate.md",
                kind: DiagnosticKind::DuplicateBasename,
            },
        ],
    }];

    for test_case in &test_cases {
        let root = helpers::write_temp_tree(&[], test_case.files);
        let result = discover_memory(&root);
        let expected: Vec<(&str, DiagnosticKind)> = test_case
            .expected_diagnostics
            .iter()
            .map(|diagnostic| (diagnostic.path, diagnostic.kind))
            .collect();

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
        assert_eq!(
            helpers::diagnostic_rows(&result),
            expected,
            "{}",
            test_case.description
        );
        helpers::remove_temp_tree(&root);
    }
}
