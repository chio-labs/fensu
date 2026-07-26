//! Corpus loading, title validation, isolation, and ordering behavior.

use crate::helpers;
use crate::test_types::{
    ExpectedCorpusDiagnostic, FixtureFile, MixedCorpusTestCase, OrderingTestCase,
    TitleValidationTestCase,
};
use fensu_memory::corpus::main::load_memory_corpus::load_memory_corpus;
use fensu_memory::corpus::types::CorpusDiagnosticKind;

#[test]
fn given_mixed_documents_when_loading_corpus_then_preserves_failures_and_parses_valid_siblings() {
    let test_cases = [MixedCorpusTestCase {
        description: "keeps missing-title skills and invalid UTF-8 notes beside a valid task",
        files: &[
            FixtureFile {
                path: ".ai/tasks/not-started/20260717T120000_000000Z__FEAT-valid-task.md",
                contents: b"# Valid Task\n\n###### Any subordinate structure\n",
            },
            FixtureFile {
                path: ".ai/knowledge/repo/skills/titleless/SKILL.md",
                contents: b"## Skill instructions\n",
            },
            FixtureFile {
                path: ".ai/knowledge/repo/notes/20260717T120001_000000Z__NOTE-invalid-utf8.md",
                contents: b"# Invalid \xff\n",
            },
        ],
        expected_document_paths: &[
            ".ai/knowledge/repo/notes/20260717T120001_000000Z__NOTE-invalid-utf8.md",
            ".ai/knowledge/repo/skills/titleless/SKILL.md",
            ".ai/tasks/not-started/20260717T120000_000000Z__FEAT-valid-task.md",
        ],
        expected_titles: &[None, None, Some("Valid Task")],
        expected_diagnostics: &[
            ExpectedCorpusDiagnostic {
                path: ".ai/knowledge/repo/notes/20260717T120001_000000Z__NOTE-invalid-utf8.md",
                kind: CorpusDiagnosticKind::InvalidUtf8,
            },
            ExpectedCorpusDiagnostic {
                path: ".ai/knowledge/repo/skills/titleless/SKILL.md",
                kind: CorpusDiagnosticKind::MissingOrEmptyTitle,
            },
            ExpectedCorpusDiagnostic {
                path: ".ai/knowledge/repo/skills/titleless/SKILL.md",
                kind: CorpusDiagnosticKind::FirstHeadingNotH1,
            },
        ],
    }];

    for test_case in &test_cases {
        let root = helpers::write_temp_tree(test_case.files);
        let corpus = load_memory_corpus(&root);
        let expected_diagnostics: Vec<(&str, CorpusDiagnosticKind)> = test_case
            .expected_diagnostics
            .iter()
            .map(|diagnostic| (diagnostic.path, diagnostic.kind))
            .collect();

        assert_eq!(
            helpers::document_paths(&corpus),
            test_case.expected_document_paths,
            "{}",
            test_case.description
        );
        assert_eq!(
            helpers::parsed_titles(&corpus),
            test_case.expected_titles,
            "{}",
            test_case.description
        );
        assert_eq!(
            helpers::diagnostic_rows(&corpus),
            expected_diagnostics,
            "{}",
            test_case.description
        );
        helpers::remove_temp_tree(&root);
    }
}

#[test]
fn given_multiple_and_late_h1_headings_when_loading_corpus_then_rejects_invalid_titles() {
    let test_cases = [TitleValidationTestCase {
        description: "rejects a second H1 and an H1 authored after a subordinate heading",
        files: &[
            FixtureFile {
                path: ".ai/knowledge/repo/notes/20260717T120003_000000Z__NOTE-late-title.md",
                contents: b"## Context\n\n# Late Title\n",
            },
            FixtureFile {
                path: ".ai/knowledge/repo/decisions/20260717T120002_000000Z__ADR-many-titles.md",
                contents: b"# First Title\n\n## Context\n\n# Second Title\n",
            },
        ],
        expected_titles: &[None, None],
        expected_diagnostics: &[
            ExpectedCorpusDiagnostic {
                path: ".ai/knowledge/repo/decisions/20260717T120002_000000Z__ADR-many-titles.md",
                kind: CorpusDiagnosticKind::MultipleH1Titles,
            },
            ExpectedCorpusDiagnostic {
                path: ".ai/knowledge/repo/notes/20260717T120003_000000Z__NOTE-late-title.md",
                kind: CorpusDiagnosticKind::FirstHeadingNotH1,
            },
        ],
    }];

    for test_case in &test_cases {
        let root = helpers::write_temp_tree(test_case.files);
        let corpus = load_memory_corpus(&root);
        let expected_diagnostics: Vec<(&str, CorpusDiagnosticKind)> = test_case
            .expected_diagnostics
            .iter()
            .map(|diagnostic| (diagnostic.path, diagnostic.kind))
            .collect();

        assert_eq!(
            helpers::parsed_titles(&corpus),
            test_case.expected_titles,
            "{}",
            test_case.description
        );
        assert_eq!(
            helpers::diagnostic_rows(&corpus),
            expected_diagnostics,
            "{}",
            test_case.description
        );
        helpers::remove_temp_tree(&root);
    }
}

#[test]
fn given_unsorted_sources_when_loading_corpus_then_orders_every_output_by_portable_path() {
    let test_cases = [OrderingTestCase {
        description: "sorts documents, skill files, source diagnostics, and corpus diagnostics",
        files: &[
            FixtureFile {
                path: ".ai/z-invalid.md",
                contents: b"ignored\n",
            },
            FixtureFile {
                path: ".ai/knowledge/repo/skills/z-skill/references/z.txt",
                contents: b"support\n",
            },
            FixtureFile {
                path: ".ai/knowledge/repo/skills/z-skill/assets/a.txt",
                contents: b"support\n",
            },
            FixtureFile {
                path: ".ai/knowledge/repo/skills/z-skill/SKILL.md",
                contents: b"# Z Skill\n",
            },
            FixtureFile {
                path: ".ai/tasks/completed/20260717T120005_000000Z__FIX-z-document.md",
                contents: b"## Context\n# Late\n# Extra\n",
            },
            FixtureFile {
                path: ".ai/knowledge/repo/notes/20260717T120004_000000Z__NOTE-a-document.md",
                contents: b"body without headings\n",
            },
            FixtureFile {
                path: ".ai/a-invalid.md",
                contents: b"ignored\n",
            },
        ],
        expected_document_paths: &[
            ".ai/knowledge/repo/notes/20260717T120004_000000Z__NOTE-a-document.md",
            ".ai/knowledge/repo/skills/z-skill/SKILL.md",
            ".ai/tasks/completed/20260717T120005_000000Z__FIX-z-document.md",
        ],
        expected_skill_file_paths: &[
            ".ai/knowledge/repo/skills/z-skill/assets/a.txt",
            ".ai/knowledge/repo/skills/z-skill/references/z.txt",
        ],
        expected_source_diagnostic_paths: &[".ai/a-invalid.md", ".ai/z-invalid.md"],
        expected_diagnostics: &[
            ExpectedCorpusDiagnostic {
                path: ".ai/knowledge/repo/notes/20260717T120004_000000Z__NOTE-a-document.md",
                kind: CorpusDiagnosticKind::MissingOrEmptyTitle,
            },
            ExpectedCorpusDiagnostic {
                path: ".ai/tasks/completed/20260717T120005_000000Z__FIX-z-document.md",
                kind: CorpusDiagnosticKind::FirstHeadingNotH1,
            },
            ExpectedCorpusDiagnostic {
                path: ".ai/tasks/completed/20260717T120005_000000Z__FIX-z-document.md",
                kind: CorpusDiagnosticKind::MultipleH1Titles,
            },
        ],
    }];

    for test_case in &test_cases {
        let root = helpers::write_temp_tree(test_case.files);
        let corpus = load_memory_corpus(&root);
        let expected_diagnostics: Vec<(&str, CorpusDiagnosticKind)> = test_case
            .expected_diagnostics
            .iter()
            .map(|diagnostic| (diagnostic.path, diagnostic.kind))
            .collect();

        assert_eq!(
            helpers::document_paths(&corpus),
            test_case.expected_document_paths,
            "{}",
            test_case.description
        );
        assert_eq!(
            helpers::skill_file_paths(&corpus),
            test_case.expected_skill_file_paths,
            "{}",
            test_case.description
        );
        assert_eq!(
            helpers::source_diagnostic_paths(&corpus),
            test_case.expected_source_diagnostic_paths,
            "{}",
            test_case.description
        );
        assert_eq!(
            helpers::diagnostic_rows(&corpus),
            expected_diagnostics,
            "{}",
            test_case.description
        );
        helpers::remove_temp_tree(&root);
    }
}
