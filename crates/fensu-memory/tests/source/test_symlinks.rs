//! Unix symlink rejection behavior for canonical sources and parents.

use fensu_memory::source::main::discover_memory::discover_memory;
use fensu_memory::source::types::DiagnosticKind;

use crate::helpers;
use crate::test_types::{
    ExpectedDiagnostic, FixtureDirectory, FixtureFile, FixtureSymlink, SymlinkDiscoveryTestCase,
};

#[cfg(unix)]
#[test]
fn given_symlinked_file_and_parent_when_discovering_then_rejects_both_without_following() {
    let test_cases = [SymlinkDiscoveryTestCase {
        description: "rejects a canonical document symlink and a canonical directory symlink",
        directories: &[
            FixtureDirectory {
                path: ".ai/knowledge/repo/notes",
            },
            FixtureDirectory { path: ".ai/tasks" },
            FixtureDirectory {
                path: "outside/tasks",
            },
        ],
        files: &[FixtureFile {
            path: "outside/20260717T120000_000000Z__NOTE-escape.md",
            contents: "body\n",
        }],
        symlinks: &[
            FixtureSymlink {
                path: ".ai/knowledge/repo/notes/20260717T120000_000000Z__NOTE-escape.md",
                target: "outside/20260717T120000_000000Z__NOTE-escape.md",
            },
            FixtureSymlink {
                path: ".ai/tasks/not-started",
                target: "outside/tasks",
            },
        ],
        expected_document_count: 0,
        expected_diagnostics: &[
            ExpectedDiagnostic {
                path: ".ai/knowledge/repo/notes/20260717T120000_000000Z__NOTE-escape.md",
                kind: DiagnosticKind::SymlinkRejected,
            },
            ExpectedDiagnostic {
                path: ".ai/tasks/not-started",
                kind: DiagnosticKind::SymlinkRejected,
            },
        ],
    }];

    for test_case in &test_cases {
        let root = helpers::write_temp_tree(test_case.directories, test_case.files);
        helpers::write_symlinks(&root, test_case.symlinks);
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
