//! Svelte script, rune, compatibility, and source-position tests.

use fensu_svelte::{parse, ScriptContext};

use crate::test_types;

#[test]
fn given_dual_scripts_when_parsing_then_preserves_expected_contexts_and_global_offsets() {
    let test_cases = [test_types::DualScriptTestCase {
        description: "module and instance script facts retain original component positions",
        source: concat!(
            "<script context=\"module\" lang=\"ts\">\n",
            "import type { Contract } from './contract';\n",
            "const shared = $state(0);\n",
            "</script>\n",
            "<script lang=\"ts\">\n",
            "export function run(): void { const inferred = build(); }\n",
            "</script>\n",
            "<p>{shared}</p>\n",
        ),
        expected_module_line: 2,
        expected_import_line: 2,
        expected_local_line: 6,
        expected_local_column: 36,
        expected_local_text: "inferred",
    }];

    for test_case in &test_cases {
        let facts = parse(test_case.source.as_bytes()).expect("must parse");
        let module = &facts.scripts[0];
        let instance = &facts.scripts[1];
        let imported = &module.facts.imports[0];
        let local = &instance.facts.local_bindings[0];

        assert_eq!(
            module.context,
            ScriptContext::Module,
            "{}",
            test_case.description
        );
        assert_eq!(
            instance.context,
            ScriptContext::Instance,
            "{}",
            test_case.description
        );
        assert_eq!(
            module.content_span.line, test_case.expected_module_line,
            "{}",
            test_case.description
        );
        assert_eq!(
            imported.span.line, test_case.expected_import_line,
            "{}",
            test_case.description
        );
        assert_eq!(
            local.span.line, test_case.expected_local_line,
            "{}",
            test_case.description
        );
        assert_eq!(
            local.span.column, test_case.expected_local_column,
            "{}",
            test_case.description
        );
        assert_eq!(
            &test_case.source[local.span.start..local.span.end],
            test_case.expected_local_text,
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_module_runes_when_parsing_then_collects_expected_top_level_calls_only() {
    let test_cases = [
        test_types::RuneTestCase {
            description: "module rune calls are collected while nested function runes are excluded",
            source: concat!(
                "<script module lang=\"ts\">\r\n",
                "const $stateValue = $state(0);\r\n",
                "const derived = $derived.by(() => state);\r\n",
                "function nested(): void { const local = $state(1); }\r\n",
                "</script>\r\n",
            ),
            expected_runes: &[("$state", 2, 20), ("$derived.by", 3, 16)],
        },
        test_types::RuneTestCase {
            description:
                "known member runes are collected while dollar-prefixed near misses are ignored",
            source: concat!(
                "<script module>\n",
                "const raw = $state.raw({});\n",
                "const unknown = $foo();\n",
                "</script>\n",
            ),
            expected_runes: &[("$state.raw", 2, 12)],
        },
        test_types::RuneTestCase {
            description: "a destructured instance binding records its rune initializer",
            source: concat!(
                "<script lang=\"ts\">\n",
                "let { children }: Props = $props();\n",
                "const nearMiss = $propsFactory();\n",
                "</script>\n",
            ),
            expected_runes: &[("$props", 2, 26)],
        },
    ];

    for test_case in &test_cases {
        let facts = parse(test_case.source.as_bytes()).expect("must parse");
        let runes: Vec<(&str, usize, usize)> = facts
            .module_runes
            .iter()
            .map(|rune| (rune.name.as_str(), rune.span.line, rune.span.column))
            .collect();

        assert_eq!(runes, test_case.expected_runes, "{}", test_case.description);
    }
}

#[test]
fn given_valid_template_bindings_when_parsing_then_accepts_compiler_syntax() {
    let test_cases = [
        test_types::TemplateSuccessTestCase {
            description: "JavaScript each and snippet bindings accept destructuring and defaults",
            source: concat!(
                "{#each items as { value, count = 0 }}<p>{value}</p>{/each}\n",
                "{#snippet item(value = 1, { label = 'x' })}<p>{label}</p>{/snippet}\n",
            ),
            expected_script_count: 0,
        },
        test_types::TemplateSuccessTestCase {
            description: "TypeScript bindings accept annotations and generic snippet parameters",
            source: concat!(
                "<script lang=\"ts\">\n",
                "type Item = { value: string; count?: number };\n",
                "type Props = { label?: string };\n",
                "const items: Item[] = [];\n",
                "</script>\n",
                "{#each items as { value, count = 0 }: Item}<p>{value}</p>{/each}\n",
                "{#snippet item<T extends Item = Item>(value: T, { label = 'x' }: Props)}",
                "<p>{value.value}{label}</p>{/snippet}\n",
            ),
            expected_script_count: 1,
        },
        test_types::TemplateSuccessTestCase {
            description: "a later TypeScript script controls an earlier template expression",
            source: concat!(
                "<p>{value as string}</p>\n",
                "<script lang=\"ts\">const value: unknown = 'value';</script>\n",
            ),
            expected_script_count: 1,
        },
    ];

    for test_case in &test_cases {
        let facts = parse(test_case.source.as_bytes()).expect("must parse");

        assert_eq!(
            facts.scripts.len(),
            test_case.expected_script_count,
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_spaced_script_attributes_when_parsing_then_recognizes_module_typescript() {
    let test_cases = [test_types::ScriptContextTestCase {
        description: "whitespace and quote style do not change script attribute semantics",
        source: concat!(
            "<script context = 'module' lang = \"ts\">\n",
            "export function typed(value: string): string { return value; }\n",
            "</script>\n",
        ),
        expected_context: ScriptContext::Module,
        expected_function_count: 1,
    }];

    for test_case in &test_cases {
        let facts = parse(test_case.source.as_bytes()).expect("must parse");

        assert_eq!(
            facts.scripts[0].context, test_case.expected_context,
            "{}",
            test_case.description
        );
        assert_eq!(
            facts.scripts[0].facts.functions.len(),
            test_case.expected_function_count,
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_nested_resources_when_parsing_then_only_top_level_resources_are_semantic() {
    let test_cases = [test_types::CompatibilityTestCase {
        description: "nested script and style elements do not become component resources",
        source: concat!(
            "<div><script>function nested() {}</script><style></style></div>\n",
            "<script>function top() {}</script>\n",
            "<style></style>\n",
        ),
        expected_script_count: 1,
    }];

    for test_case in &test_cases {
        let facts = parse(test_case.source.as_bytes()).expect("must parse");

        assert_eq!(
            facts.scripts.len(),
            test_case.expected_script_count,
            "{}",
            test_case.description
        );
        assert_eq!(
            facts.scripts[0].facts.functions[0].name, "top",
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_svelte_five_constructs_when_parsing_then_accepts_expected_supported_grammar() {
    let test_cases = [test_types::CompatibilityTestCase {
        description: "snippet type parameters, render tags, and attach tags parse together",
        source: concat!(
            "<script lang=\"ts\">\n",
            "const attach = (node: Element): void => { void node; };\n",
            "</script>\n",
            "{#snippet item<T>(value: T)}<span>{value}</span>{/snippet}\n",
            "{@render item('value')}\n",
            "<div {@attach attach}></div>\n",
        ),
        expected_script_count: 1,
    }];

    for test_case in &test_cases {
        let facts = parse(test_case.source.as_bytes()).expect("must parse");

        assert_eq!(
            facts.scripts.len(),
            test_case.expected_script_count,
            "{}",
            test_case.description
        );
        assert_eq!(
            facts.scripts[0].context,
            ScriptContext::Instance,
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_bom_crlf_and_unicode_when_parsing_then_preserves_expected_original_byte_positions() {
    let test_cases = [test_types::ClassPositionTestCase {
        description: "a Unicode class name after a BOM and CRLF retains its original byte span",
        source:
            "\u{feff}<h1>é</h1>\r\n<script lang=\"ts\">\r\nexport class Café {}\r\n</script>\r\n",
        expected_line: 3,
        expected_column: 13,
        expected_text: "Café",
    }];

    for test_case in &test_cases {
        let facts = parse(test_case.source.as_bytes()).expect("must parse");
        let class = &facts.scripts[0].facts.classes[0];

        assert_eq!(
            class.span.line, test_case.expected_line,
            "{}",
            test_case.description
        );
        assert_eq!(
            class.span.column, test_case.expected_column,
            "{}",
            test_case.description
        );
        assert_eq!(
            &test_case.source[class.span.start..class.span.end],
            test_case.expected_text,
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_duplicate_script_context_when_parsing_then_rejects_expected_second_script() {
    let test_cases = [test_types::DuplicateScriptTestCase {
        description: "the second instance script is rejected at its opening tag",
        source: b"<script>const first = 1;</script>\n<script>const second = 2;</script>",
        expected_message: "duplicate Instance script",
        expected_line: 2,
        expected_column: 0,
    }];

    for test_case in &test_cases {
        let diagnostic = parse(test_case.source).expect_err("must fail");

        assert_eq!(
            diagnostic.message, test_case.expected_message,
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
    }
}
