//! Live non-writing memory summary behavior.

use std::fs;

use fensu_memory::engine::main::summarize_memory::summarize_memory;

use crate::dependencies::helpers;
use crate::test_types::{FixtureFile, MemorySummaryTestCase};

#[test]
fn given_repository_memory_when_summarizing_then_counts_live_corpus_without_database() {
    let test_cases = [MemorySummaryTestCase {
        description: "counts valid and invalid corpus facts plus graph diagnostics",
        files: &[
            FixtureFile {
                path: ".ai/knowledge/repo/notes/20260717T120001_000000Z__NOTE-live.md",
                contents: b"# Live\n\nPreamble [[note:missing]] #overview.\n\n## Detail\n\n- Remember this.\n",
            },
            FixtureFile {
                path: ".ai/knowledge/repo/notes/20260717T120002_000000Z__NOTE-invalid.md",
                contents: b"Document without a title.\n",
            },
        ],
        expected_summary_counts: [2, 2, 1, 1, 1, 0, 0, 1, 1],
        expected_database_exists: false,
    }];

    for test_case in &test_cases {
        let root = helpers::write_repository(test_case.files);
        let summary = summarize_memory(&root);
        let counts = [
            summary.document_count,
            summary.section_count,
            summary.list_item_count,
            summary.link_count,
            summary.tag_count,
            summary.skill_file_count,
            summary.source_diagnostic_count,
            summary.corpus_diagnostic_count,
            summary.graph_diagnostic_count,
        ];
        let database_path = root.join("generated/index/memory.sqlite3");

        assert_eq!(
            counts, test_case.expected_summary_counts,
            "{}: live summary counts",
            test_case.description
        );
        assert_eq!(
            database_path.exists(),
            test_case.expected_database_exists,
            "{}: database creation",
            test_case.description
        );
        fs::remove_dir_all(root).expect("summary repository is removable");
    }
}
