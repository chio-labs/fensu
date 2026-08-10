//! Strict Svelte structure and embedded TypeScript diagnostic tests.

use fensu_svelte::parse;

use crate::test_types;

#[test]
fn given_malformed_embedded_typescript_when_parsing_then_reports_expected_global_position() {
    let test_cases = [test_types::DiagnosticTestCase {
        description: "embedded Oxc offsets are rebased after preceding Unicode markup",
        source: "<h1>é</h1>\n<script lang=\"ts\">\nconst value = ;\n</script>\n".as_bytes(),
        expected_message: None,
        expected_message_prefix: None,
        expected_line: 3,
        expected_column: Some(14),
        expected_start: Some(45),
    }];

    for test_case in &test_cases {
        let diagnostic = parse(test_case.source).expect_err("must fail");
        assert_eq!(
            diagnostic.span.line, test_case.expected_line,
            "{}",
            test_case.description
        );
        assert_eq!(
            diagnostic.span.column,
            test_case.expected_column.unwrap_or_default(),
            "{}",
            test_case.description
        );
        assert_eq!(
            diagnostic.span.start,
            test_case.expected_start.unwrap_or_default(),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_malformed_template_expressions_when_parsing_then_reports_expected_global_positions() {
    let test_cases = [
        test_types::DiagnosticTestCase {
            description: "markup expression diagnostics are rebased after Unicode markup",
            source: "<h1>é</h1>\n<p>{value +}</p>".as_bytes(),
            expected_message: None,
            expected_message_prefix: None,
            expected_line: 2,
            expected_column: Some(11),
            expected_start: Some(23),
        },
        test_types::DiagnosticTestCase {
            description: "block expression diagnostics are rebased to component positions",
            source: "<h1>é</h1>\n{#if value +}<p>broken</p>{/if}".as_bytes(),
            expected_message: None,
            expected_message_prefix: None,
            expected_line: 2,
            expected_column: Some(12),
            expected_start: Some(24),
        },
    ];

    for test_case in &test_cases {
        let diagnostic = parse(test_case.source).expect_err("must fail");

        assert_eq!(
            diagnostic.span.line, test_case.expected_line,
            "{}",
            test_case.description
        );
        assert_eq!(
            diagnostic.span.column,
            test_case.expected_column.unwrap_or_default(),
            "{}",
            test_case.description
        );
        assert_eq!(
            diagnostic.span.start,
            test_case.expected_start.unwrap_or_default(),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_empty_template_expression_when_parsing_then_rejects_exact_empty_span() {
    let test_cases = [
        test_types::DiagnosticTestCase {
            description: "an expression interpolation must contain an expression",
            source: b"<p>{}</p>",
            expected_message: Some("empty template expression"),
            expected_message_prefix: None,
            expected_line: 1,
            expected_column: Some(3),
            expected_start: Some(3),
        },
        test_types::DiagnosticTestCase {
            description: "whitespace does not make an expression interpolation non-empty",
            source: b"<p>{   }</p>",
            expected_message: Some("invalid Svelte structure: ERROR"),
            expected_message_prefix: None,
            expected_line: 1,
            expected_column: Some(4),
            expected_start: Some(4),
        },
    ];

    for test_case in &test_cases {
        let diagnostic = parse(test_case.source).expect_err("must fail");

        assert_eq!(
            diagnostic.message,
            test_case.expected_message.unwrap_or_default(),
            "{}",
            test_case.description
        );
        assert_eq!(
            diagnostic.span.start,
            test_case.expected_start.unwrap_or_default(),
            "{}",
            test_case.description
        );
        assert_eq!(
            diagnostic.span.column,
            test_case.expected_column.unwrap_or_default(),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_invalid_template_binding_syntax_when_parsing_then_rejects_oxc_near_misses() {
    let test_cases = [
        test_types::DiagnosticTestCase {
            description: "an each binding cannot be an addition expression",
            source: b"{#each items as foo + bar}{/each}",
            expected_message: Some("Missing initializer in const declaration"),
            expected_message_prefix: None,
            expected_line: 1,
            expected_column: Some(16),
            expected_start: Some(16),
        },
        test_types::DiagnosticTestCase {
            description: "a snippet parameter cannot be an addition expression",
            source: b"{#snippet item(value + 1)}{/snippet}",
            expected_message: Some("Expected `,` or `)` but found `+`"),
            expected_message_prefix: None,
            expected_line: 1,
            expected_column: Some(21),
            expected_start: Some(21),
        },
        test_types::DiagnosticTestCase {
            description: "snippet TypeScript syntax is rejected in a JavaScript component",
            source: b"{#snippet item<T>(value: T)}{/snippet}",
            expected_message: Some("Expected `(` but found `<`"),
            expected_message_prefix: None,
            expected_line: 1,
            expected_column: Some(14),
            expected_start: Some(14),
        },
        test_types::DiagnosticTestCase {
            description: "a TypeScript assertion is rejected without a TypeScript script",
            source: b"<p>{value as string}</p>",
            expected_message: Some(
                "Type assertion expressions can only be used in TypeScript files.",
            ),
            expected_message_prefix: None,
            expected_line: 1,
            expected_column: Some(4),
            expected_start: Some(4),
        },
    ];

    for test_case in &test_cases {
        let diagnostic = parse(test_case.source).expect_err("must fail");

        assert_eq!(
            diagnostic.message,
            test_case.expected_message.unwrap_or_default(),
            "{}",
            test_case.description
        );
        assert_eq!(
            diagnostic.span.start,
            test_case.expected_start.unwrap_or_default(),
            "{}",
            test_case.description
        );
        assert_eq!(
            diagnostic.span.column,
            test_case.expected_column.unwrap_or_default(),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_missing_snippet_name_when_parsing_then_rejects_zero_width_name() {
    let test_cases = [
        test_types::DiagnosticTestCase {
            description: "a snippet with empty parentheses has no name",
            source: b"{#snippet ()}{/snippet}",
            expected_message: Some("snippet name is required"),
            expected_message_prefix: None,
            expected_line: 1,
            expected_column: Some(0),
            expected_start: Some(0),
        },
        test_types::DiagnosticTestCase {
            description: "a snippet closing immediately has no name",
            source: b"{#snippet}{/snippet}",
            expected_message: Some("snippet name is required"),
            expected_message_prefix: None,
            expected_line: 1,
            expected_column: Some(0),
            expected_start: Some(0),
        },
    ];

    for test_case in &test_cases {
        let diagnostic = parse(test_case.source).expect_err("must fail");

        assert_eq!(
            diagnostic.message,
            test_case.expected_message.unwrap_or_default(),
            "{}",
            test_case.description
        );
        assert_eq!(
            diagnostic.span.start,
            test_case.expected_start.unwrap_or_default(),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_named_recovery_forms_when_parsing_then_rejects_each_exact_kind() {
    let test_cases = [
        test_types::DiagnosticTestCase {
            description: "an attribute quote without equals is typed recovery",
            source: b"<div title\"broken\"></div>",
            expected_message: Some("invalid Svelte structure: attribute_expected_equals_tail"),
            expected_message_prefix: None,
            expected_line: 1,
            expected_column: None,
            expected_start: None,
        },
        test_types::DiagnosticTestCase {
            description: "a stray attribute brace is typed recovery",
            source: b"<div }></div>",
            expected_message: Some("invalid Svelte structure: attribute_sequence_recovery_tail"),
            expected_message_prefix: None,
            expected_line: 1,
            expected_column: None,
            expected_start: None,
        },
        test_types::DiagnosticTestCase {
            description: "an unmatched closing tag is typed recovery",
            source: b"</div>",
            expected_message: Some("invalid Svelte structure: erroneous_end_tag"),
            expected_message_prefix: None,
            expected_line: 1,
            expected_column: None,
            expected_start: None,
        },
        test_types::DiagnosticTestCase {
            description: "an unterminated attribute expression is typed recovery",
            source: b"<div title={ >",
            expected_message: Some("invalid Svelte structure: incomplete_attribute_expression"),
            expected_message_prefix: None,
            expected_line: 1,
            expected_column: None,
            expected_start: None,
        },
        test_types::DiagnosticTestCase {
            description: "whitespace before a block sigil is typed recovery",
            source: b"{ #if visible}",
            expected_message: Some("invalid Svelte structure: malformed_block"),
            expected_message_prefix: None,
            expected_line: 1,
            expected_column: None,
            expected_start: None,
        },
        test_types::DiagnosticTestCase {
            description: "a branch outside its block is typed recovery",
            source: b"{:else}",
            expected_message: Some("invalid Svelte structure: orphan_branch"),
            expected_message_prefix: None,
            expected_line: 1,
            expected_column: None,
            expected_start: None,
        },
        test_types::DiagnosticTestCase {
            description: "a tag keyword without trailing whitespace is typed recovery",
            source: b"{@htmlvalue}",
            expected_message: Some("invalid Svelte structure: tag_missing_whitespace_trailing"),
            expected_message_prefix: None,
            expected_line: 1,
            expected_column: None,
            expected_start: None,
        },
    ];

    for test_case in &test_cases {
        let diagnostic = parse(test_case.source).expect_err("must fail");

        assert_eq!(
            diagnostic.message,
            test_case.expected_message.unwrap_or_default(),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_invalid_script_resources_when_parsing_then_rejects_expected_resource() {
    let test_cases = [
        test_types::DiagnosticTestCase {
            description: "a non-module context value is rejected",
            source: b"<script context=\"instance\"></script>",
            expected_message: Some("invalid script context attribute"),
            expected_message_prefix: None,
            expected_line: 1,
            expected_column: Some(8),
            expected_start: None,
        },
        test_types::DiagnosticTestCase {
            description: "a valued module attribute is rejected",
            source: b"<script module=\"module\"></script>",
            expected_message: Some("invalid script context attribute"),
            expected_message_prefix: None,
            expected_line: 1,
            expected_column: Some(8),
            expected_start: None,
        },
        test_types::DiagnosticTestCase {
            description: "multiple context declarations on one script are rejected",
            source: b"<script module context=\"module\"></script>",
            expected_message: Some("duplicate script context attribute"),
            expected_message_prefix: None,
            expected_line: 1,
            expected_column: Some(15),
            expected_start: None,
        },
        test_types::DiagnosticTestCase {
            description: "a second top-level style is rejected",
            source: b"<style>p { color: red; }</style>\n<style>p { color: blue; }</style>",
            expected_message: Some("duplicate top-level style"),
            expected_message_prefix: None,
            expected_line: 2,
            expected_column: Some(0),
            expected_start: None,
        },
    ];

    for test_case in &test_cases {
        let diagnostic = parse(test_case.source).expect_err("must fail");

        assert_eq!(
            diagnostic.message,
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
            diagnostic.span.column,
            test_case.expected_column.unwrap_or_default(),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_malformed_block_when_parsing_then_rejects_expected_recovery_structure() {
    let test_cases = [test_types::DiagnosticTestCase {
        description: "a mismatched control-flow closing block is rejected",
        source: b"{#if visible}<p>open{/each}",
        expected_message: None,
        expected_message_prefix: Some("invalid Svelte structure:"),
        expected_line: 1,
        expected_column: None,
        expected_start: None,
    }];

    for test_case in &test_cases {
        let diagnostic = parse(test_case.source).expect_err("must fail");

        assert_eq!(
            diagnostic.span.line, test_case.expected_line,
            "{}",
            test_case.description
        );
        assert!(
            diagnostic
                .message
                .starts_with(test_case.expected_message_prefix.unwrap_or_default()),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_invalid_dotted_component_closing_tags_when_parsing_then_reports_original_offsets() {
    let test_cases = [
        test_types::DiagnosticTestCase {
            description: "a mismatched dotted component member is rejected at its closing tag",
            source: b"<Card.Root><p>value</p></Card.Other>",
            expected_message: None,
            expected_message_prefix: Some("invalid Svelte structure:"),
            expected_line: 1,
            expected_column: Some(23),
            expected_start: Some(23),
        },
        test_types::DiagnosticTestCase {
            description: "an unterminated dotted component closing tag remains invalid",
            source: b"<Card.Root>value</Card.Root",
            expected_message: None,
            expected_message_prefix: Some("invalid Svelte structure:"),
            expected_line: 1,
            expected_column: Some(27),
            expected_start: Some(27),
        },
    ];

    for test_case in &test_cases {
        let diagnostic = parse(test_case.source).expect_err("must fail");

        assert_eq!(
            diagnostic.span.line, test_case.expected_line,
            "{}",
            test_case.description
        );
        assert_eq!(
            diagnostic.span.column,
            test_case.expected_column.unwrap_or_default(),
            "{}",
            test_case.description
        );
        assert_eq!(
            diagnostic.span.start,
            test_case.expected_start.unwrap_or_default(),
            "{}",
            test_case.description
        );
        assert!(
            diagnostic
                .message
                .starts_with(test_case.expected_message_prefix.unwrap_or_default()),
            "{}: {}",
            test_case.description,
            diagnostic.message
        );
    }
}

#[test]
fn given_incomplete_attribute_when_parsing_then_rejects_expected_named_recovery_form() {
    let test_cases = [test_types::DiagnosticTestCase {
        description: "an attribute missing its value is rejected even when the grammar recovers",
        source: b"<button disabled=>broken</button>",
        expected_message: None,
        expected_message_prefix: Some("invalid Svelte structure:"),
        expected_line: 1,
        expected_column: None,
        expected_start: None,
    }];

    for test_case in &test_cases {
        let diagnostic = parse(test_case.source).expect_err("must fail");

        assert_eq!(
            diagnostic.span.line, test_case.expected_line,
            "{}",
            test_case.description
        );
        assert!(
            diagnostic
                .message
                .starts_with(test_case.expected_message_prefix.unwrap_or_default()),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_invalid_utf8_when_parsing_then_rejects_at_expected_invalid_byte() {
    let test_cases = [test_types::DiagnosticTestCase {
        description: "invalid component bytes fail before tree-sitter parsing",
        source: b"<p>\xff</p>",
        expected_message: Some("source is not valid UTF-8"),
        expected_message_prefix: None,
        expected_line: 1,
        expected_column: Some(3),
        expected_start: Some(3),
    }];

    for test_case in &test_cases {
        let diagnostic = parse(test_case.source).expect_err("must fail");

        assert_eq!(
            diagnostic.message.as_str(),
            test_case.expected_message.unwrap_or_default(),
            "{}",
            test_case.description
        );
        assert_eq!(
            diagnostic.span.start,
            test_case.expected_start.unwrap_or_default(),
            "{}",
            test_case.description
        );
        assert_eq!(
            diagnostic.span.column,
            test_case.expected_column.unwrap_or_default(),
            "{}",
            test_case.description
        );
    }
}
