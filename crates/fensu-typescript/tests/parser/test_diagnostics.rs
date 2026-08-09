//! Strict UTF-8 and deterministic parse diagnostic tests.

use fensu_typescript::{parse, SourceKind};

use crate::test_types;

#[test]
fn given_malformed_source_when_parsing_then_reports_expected_earliest_position() {
    let test_cases = [test_types::DiagnosticTestCase {
        description: "the first of multiple malformed constructs owns the diagnostic",
        source: b"const first = ;\nconst second = ;\n",
        source_kind: SourceKind::TypeScript,
        expected_message: None,
        expected_line: 1,
        expected_column: 14,
        expected_start: 14,
    }];

    for test_case in &test_cases {
        let diagnostic = parse(test_case.source, test_case.source_kind).expect_err("must fail");

        assert_eq!(
            diagnostic.span.line, test_case.expected_line,
            "{}",
            test_case.description
        );
        assert_eq!(
            diagnostic.span.column, test_case.expected_column,
            "{}",
            test_case.description
        );
        assert_eq!(
            diagnostic.span.start, test_case.expected_start,
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_invalid_utf8_when_parsing_then_rejects_at_expected_byte() {
    let test_cases = [test_types::DiagnosticTestCase {
        description: "an invalid byte is rejected before Oxc parsing",
        source: b"const name = \xff;",
        source_kind: SourceKind::TypeScript,
        expected_message: Some("source is not valid UTF-8"),
        expected_line: 1,
        expected_column: 13,
        expected_start: 13,
    }];

    for test_case in &test_cases {
        let diagnostic = parse(test_case.source, test_case.source_kind).expect_err("must fail");

        assert_eq!(
            diagnostic.message.as_str(),
            test_case.expected_message.unwrap_or_default(),
            "{}",
            test_case.description
        );
        assert_eq!(
            diagnostic.span.line, test_case.expected_line,
            "{}",
            test_case.description
        );
        assert_eq!(
            diagnostic.span.column, test_case.expected_column,
            "{}",
            test_case.description
        );
        assert_eq!(
            diagnostic.span.start, test_case.expected_start,
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_bom_crlf_and_unicode_when_parsing_then_columns_are_expected_utf8_bytes() {
    let test_cases = [test_types::BindingPositionTestCase {
        description: "a preceding multibyte character advances the local column by two bytes",
        source: "\u{feff}export function run(): void {\r\n  void \"é\"; const inferred = build();\r\n}\r\n",
        binding_name: "inferred",
        expected_line: 2,
        expected_column: 19,
        expected_text: b"inferred",
    }];

    for test_case in &test_cases {
        let facts = parse(test_case.source.as_bytes(), SourceKind::TypeScript).expect("must parse");
        let binding = facts
            .local_bindings
            .iter()
            .find(|item| item.name == test_case.binding_name)
            .expect("binding must exist");

        assert_eq!(
            binding.span.line, test_case.expected_line,
            "{}",
            test_case.description
        );
        assert_eq!(
            binding.span.column, test_case.expected_column,
            "{}",
            test_case.description
        );
        assert_eq!(
            &test_case.source.as_bytes()[binding.span.start..binding.span.end],
            test_case.expected_text,
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_javascript_when_parsing_then_accepts_expected_module_facts() {
    let test_cases = [test_types::ParseSuccessTestCase {
        description: "JavaScript source uses the non-TypeScript Oxc mode",
        source: b"export function read(value) { return value; }\n",
        source_kind: SourceKind::JavaScript,
        expected_function_count: 1,
        expected_exported: true,
    }];

    for test_case in &test_cases {
        let facts = parse(test_case.source, test_case.source_kind).expect("must parse");

        assert_eq!(
            facts.functions.len(),
            test_case.expected_function_count,
            "{}",
            test_case.description
        );
        assert_eq!(
            facts.functions[0].exported, test_case.expected_exported,
            "{}",
            test_case.description
        );
    }
}
