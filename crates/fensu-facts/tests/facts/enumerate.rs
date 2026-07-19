//! Breadth-first traversal behavior over CPython-shaped node streams.

use fensu_facts::facts::main::enumerate_nodes::enumerate_nodes;
use ruff_python_ast::PythonVersion;

use crate::test_types;

#[test]
fn given_shape_matrix_when_enumerating_nodes_then_matches_cpython_order_and_spans() {
    let test_cases = [
        test_types::EnumerateNodesTestCase {
            description: "assignment enumerates module target then value breadth first",
            source: "x = 1\n",
            expected_kinds: &["Module", "Assign", "Name", "Constant"],
            expected_first_span: Some((1, 0, 1, 5)),
        },
        test_types::EnumerateNodesTestCase {
            description: "decorated function starts at the def keyword not the decorator",
            source: "@dec\ndef f():\n    pass\n",
            expected_kinds: &["Module", "FunctionDef", "arguments", "Pass", "Name"],
            expected_first_span: Some((2, 0, 3, 8)),
        },
        test_types::EnumerateNodesTestCase {
            description: "elif chains synthesize nested if nodes spanning the remaining chain",
            source: "if a:\n    pass\nelif b:\n    pass\nelse:\n    pass\n",
            expected_kinds: &["Module", "If", "Name", "Pass", "If", "Name", "Pass", "Pass"],
            expected_first_span: Some((1, 0, 6, 8)),
        },
        test_types::EnumerateNodesTestCase {
            description: "unparenthesized generator adopts the call argument parentheses",
            source: "f(x for x in y)\n",
            expected_kinds: &[
                "Module",
                "Expr",
                "Call",
                "Name",
                "GeneratorExp",
                "Name",
                "comprehension",
                "Name",
                "Name",
            ],
            expected_first_span: Some((1, 0, 1, 15)),
        },
        test_types::EnumerateNodesTestCase {
            description: "fstring merges adjacent literals into one constant",
            source: "x = 'a' f'b{q}c'\n",
            expected_kinds: &[
                "Module",
                "Assign",
                "Name",
                "JoinedStr",
                "Constant",
                "FormattedValue",
                "Constant",
                "Name",
            ],
            expected_first_span: Some((1, 0, 1, 16)),
        },
    ];
    for test_case in test_cases {
        let nodes = enumerate_nodes(
            test_case.source,
            PythonVersion {
                major: 3,
                minor: 12,
            },
        )
        .unwrap_or_else(|failure| {
            panic!(
                "case '{}' failed to parse: {}",
                test_case.description, failure.message
            )
        });
        let kinds: Vec<&'static str> = nodes.iter().map(|node| node.kind).collect();
        assert_eq!(
            kinds, test_case.expected_kinds,
            "case '{}' kinds diverged",
            test_case.description
        );
        let first_span = nodes.get(1).and_then(|node| node.span);
        assert_eq!(
            first_span, test_case.expected_first_span,
            "case '{}' first span diverged",
            test_case.description
        );
    }
}
