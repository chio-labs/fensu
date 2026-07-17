//! Title, preamble, heading, section, CRLF, and Unicode behavior.

use strata_memory::markdown::main::parse_markdown::parse_markdown;
use strata_memory::markdown::types::SemanticHeadingKind;

use crate::test_types::StructureTestCase;

const FLEXIBLE_DOCUMENT: &str = "# Design Memory\n\nIntro with `inline value` before sections.\n\n## Context\n\nContext body.\n\n### Phase 4AB: Unicode café\n\nPhase body.\n\n## Unexpected Observatory\n\nUnknown body.\n";
const FREEFORM_DOCUMENT: &str = "freeform 💾 without a heading\n";
const UNICODE_CRLF_DOCUMENT: &str =
    "# Καλημέρα 世界\r\n\r\nPréface.\r\n\r\n## Why This Document Exists\r\n\r\nRésumé.\r\n";

#[test]
fn given_flexible_documents_when_parsing_then_preserves_structure_and_optional_semantics() {
    let test_cases = [
        StructureTestCase {
            description:
                "extracts title, preamble, nested paths, phase metadata, and unknown sections",
            source: FLEXIBLE_DOCUMENT,
            expected_title: Some("Design Memory"),
            expected_preamble_raw: "\nIntro with `inline value` before sections.\n\n",
            expected_preamble_plain: "Intro with inline value before sections.",
            expected_heading_texts: &[
                "Design Memory",
                "Context",
                "Phase 4AB: Unicode café",
                "Unexpected Observatory",
            ],
            expected_heading_levels: &[1, 2, 3, 2],
            expected_heading_paths: &[
                &["Design Memory"],
                &["Design Memory", "Context"],
                &["Design Memory", "Context", "Phase 4AB: Unicode café"],
                &["Design Memory", "Unexpected Observatory"],
            ],
            expected_heading_lines: &[(1, 2), (5, 6), (9, 10), (13, 14)],
            expected_semantic_kinds: &[
                None,
                Some(SemanticHeadingKind::Context),
                Some(SemanticHeadingKind::Phase),
                None,
            ],
            expected_phase_identifiers: &[None, None, Some("4AB"), None],
            expected_phase_titles: &[None, None, Some("Unicode café"), None],
            expected_section_count: 3,
            expected_raw_markdown: FLEXIBLE_DOCUMENT,
        },
        StructureTestCase {
            description: "keeps Unicode bytes and CRLF line ranges stable",
            source: UNICODE_CRLF_DOCUMENT,
            expected_title: Some("Καλημέρα 世界"),
            expected_preamble_raw: "\r\nPréface.\r\n\r\n",
            expected_preamble_plain: "Préface.",
            expected_heading_texts: &["Καλημέρα 世界", "Why This Document Exists"],
            expected_heading_levels: &[1, 2],
            expected_heading_paths: &[
                &["Καλημέρα 世界"],
                &["Καλημέρα 世界", "Why This Document Exists"],
            ],
            expected_heading_lines: &[(1, 2), (5, 6)],
            expected_semantic_kinds: &[None, Some(SemanticHeadingKind::Objective)],
            expected_phase_identifiers: &[None, None],
            expected_phase_titles: &[None, None],
            expected_section_count: 1,
            expected_raw_markdown: UNICODE_CRLF_DOCUMENT,
        },
        StructureTestCase {
            description:
                "returns a generic lossless result when optional document structure is absent",
            source: FREEFORM_DOCUMENT,
            expected_title: None,
            expected_preamble_raw: FREEFORM_DOCUMENT,
            expected_preamble_plain: "freeform 💾 without a heading",
            expected_heading_texts: &[],
            expected_heading_levels: &[],
            expected_heading_paths: &[],
            expected_heading_lines: &[],
            expected_semantic_kinds: &[],
            expected_phase_identifiers: &[],
            expected_phase_titles: &[],
            expected_section_count: 0,
            expected_raw_markdown: FREEFORM_DOCUMENT,
        },
    ];

    for test_case in &test_cases {
        let result = parse_markdown(test_case.source);
        let heading_texts: Vec<&str> = result
            .headings
            .iter()
            .map(|heading| heading.text.as_str())
            .collect();
        let heading_levels: Vec<u8> = result
            .headings
            .iter()
            .map(|heading| heading.level)
            .collect();
        let heading_paths: Vec<Vec<&str>> = result
            .headings
            .iter()
            .map(|heading| heading.heading_path.iter().map(String::as_str).collect())
            .collect();
        let expected_paths: Vec<Vec<&str>> = test_case
            .expected_heading_paths
            .iter()
            .map(|path| path.to_vec())
            .collect();
        let heading_lines: Vec<(usize, usize)> = result
            .headings
            .iter()
            .map(|heading| {
                (
                    heading.source_range.start_line,
                    heading.source_range.end_line,
                )
            })
            .collect();
        let semantic_kinds: Vec<Option<SemanticHeadingKind>> = result
            .headings
            .iter()
            .map(|heading| heading.semantic_kind)
            .collect();
        let phase_identifiers: Vec<Option<&str>> = result
            .headings
            .iter()
            .map(|heading| heading.phase_identifier.as_deref())
            .collect();
        let phase_titles: Vec<Option<&str>> = result
            .headings
            .iter()
            .map(|heading| heading.phase_title.as_deref())
            .collect();

        assert_eq!(
            result.title.as_deref(),
            test_case.expected_title,
            "{}",
            test_case.description
        );
        assert_eq!(
            result.raw_markdown, test_case.expected_raw_markdown,
            "{}",
            test_case.description
        );
        assert_eq!(
            result.preamble_raw_markdown, test_case.expected_preamble_raw,
            "{}",
            test_case.description
        );
        assert_eq!(
            result.preamble_plain_text, test_case.expected_preamble_plain,
            "{}",
            test_case.description
        );
        assert_eq!(
            heading_texts, test_case.expected_heading_texts,
            "{}",
            test_case.description
        );
        assert_eq!(
            heading_levels, test_case.expected_heading_levels,
            "{}",
            test_case.description
        );
        assert_eq!(heading_paths, expected_paths, "{}", test_case.description);
        assert_eq!(
            heading_lines, test_case.expected_heading_lines,
            "{}",
            test_case.description
        );
        assert_eq!(
            semantic_kinds, test_case.expected_semantic_kinds,
            "{}",
            test_case.description
        );
        assert_eq!(
            phase_identifiers, test_case.expected_phase_identifiers,
            "{}",
            test_case.description
        );
        assert_eq!(
            phase_titles, test_case.expected_phase_titles,
            "{}",
            test_case.description
        );
        assert_eq!(
            result.sections.len(),
            test_case.expected_section_count,
            "{}",
            test_case.description
        );
    }
}
