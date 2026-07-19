//! Fenced, indented, and inline code behavior.

use fensu_memory::markdown::main::parse_markdown::parse_markdown;
use fensu_memory::markdown::types::CodeBlockKind;

use crate::test_types::CodeBlockTestCase;

const CODE_DOCUMENT: &str = "# Code Notes\n\n## Examples\n\nInline `Vec<usize>` remains text.\n\n~~~rust linenos\nlet value = 1;\n~~~\n\n    indented();\n    second_line();\n";

#[test]
fn given_fenced_indented_and_inline_code_when_parsing_then_preserves_code_content() {
    let test_cases = [CodeBlockTestCase {
        description: "retains fence info and indented content while inline code remains plain text",
        source: CODE_DOCUMENT,
        expected_kinds: &[CodeBlockKind::Fenced, CodeBlockKind::Indented],
        expected_infos: &[Some("rust linenos"), None],
        expected_languages: &[Some("rust"), None],
        expected_contents: &["let value = 1;\n", "indented();\nsecond_line();\n"],
        expected_source_lines: &[7, 11],
        expected_plain_text_fragment: "Inline Vec<usize> remains text.",
    }];

    for test_case in &test_cases {
        let result = parse_markdown(test_case.source);
        let kinds: Vec<CodeBlockKind> = result.code_blocks.iter().map(|block| block.kind).collect();
        let infos: Vec<Option<&str>> = result
            .code_blocks
            .iter()
            .map(|block| block.info.as_deref())
            .collect();
        let languages: Vec<Option<&str>> = result
            .code_blocks
            .iter()
            .map(|block| block.language.as_deref())
            .collect();
        let contents: Vec<&str> = result
            .code_blocks
            .iter()
            .map(|block| block.raw_content.as_str())
            .collect();
        let source_lines: Vec<usize> = result
            .code_blocks
            .iter()
            .map(|block| block.source_line)
            .collect();
        let section_plain = result
            .sections
            .iter()
            .map(|section| section.plain_text.as_str())
            .collect::<Vec<_>>()
            .join("\n");

        assert_eq!(kinds, test_case.expected_kinds, "{}", test_case.description);
        assert_eq!(infos, test_case.expected_infos, "{}", test_case.description);
        assert_eq!(
            languages, test_case.expected_languages,
            "{}",
            test_case.description
        );
        assert_eq!(
            contents, test_case.expected_contents,
            "{}",
            test_case.description
        );
        assert_eq!(
            source_lines, test_case.expected_source_lines,
            "{}",
            test_case.description
        );
        assert!(
            section_plain.contains(test_case.expected_plain_text_fragment),
            "{}",
            test_case.description
        );
    }
}
