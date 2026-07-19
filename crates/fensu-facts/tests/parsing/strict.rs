//! Strict-parse validity over syntax, version, and recovery fixtures.

use fensu_facts::parsing::main::parse_strict::parse_strict;
use ruff_python_ast::PythonVersion;

use crate::test_types;

#[test]
fn given_syntax_fixtures_when_parsing_strictly_then_matches_expected_validity() {
    let test_cases = [
        test_types::ParseStrictTestCase {
            description: "a plain module parses cleanly",
            source: "value: int = 1\n\n\ndef read_value() -> int:\n    return value\n",
            python_minor: 12,
            expected_valid: true,
            expected_failure_line: 0,
        },
        test_types::ParseStrictTestCase {
            description: "an empty module parses cleanly",
            source: "",
            python_minor: 12,
            expected_valid: true,
            expected_failure_line: 0,
        },
        test_types::ParseStrictTestCase {
            description: "an unterminated string is rejected at its line",
            source: "value = 1\ntext = \"open\n",
            python_minor: 12,
            expected_valid: false,
            expected_failure_line: 2,
        },
        test_types::ParseStrictTestCase {
            description: "an unclosed parenthesis is rejected at eof unlike cpython's opener line",
            source: "value = (1\n",
            python_minor: 12,
            expected_valid: false,
            expected_failure_line: 2,
        },
        test_types::ParseStrictTestCase {
            description: "a bad indent is rejected even though the parser recovers",
            source: "def read_value() -> int:\n    first = 1\n      second = 2\n    return first\n",
            python_minor: 12,
            expected_valid: false,
            expected_failure_line: 3,
        },
        test_types::ParseStrictTestCase {
            description: "nested quote reuse inside an f-string parses on 3.12",
            source: "name = 1\ntext = f\"{\"literal\"}\"\n",
            python_minor: 12,
            expected_valid: true,
            expected_failure_line: 0,
        },
        test_types::ParseStrictTestCase {
            description: "pep 695 type aliases parse on 3.12",
            source: "type Alias = int\n",
            python_minor: 12,
            expected_valid: true,
            expected_failure_line: 0,
        },
        test_types::ParseStrictTestCase {
            description: "pep 695 type aliases are version errors on 3.11",
            source: "type Alias = int\n",
            python_minor: 11,
            expected_valid: false,
            expected_failure_line: 1,
        },
        test_types::ParseStrictTestCase {
            description: "type parameter defaults are version errors on 3.12",
            source: "class Container[T = int]:\n    value: T\n",
            python_minor: 12,
            expected_valid: false,
            expected_failure_line: 1,
        },
        test_types::ParseStrictTestCase {
            description: "type parameter defaults parse on 3.13",
            source: "class Container[T = int]:\n    value: T\n",
            python_minor: 13,
            expected_valid: true,
            expected_failure_line: 0,
        },
        test_types::ParseStrictTestCase {
            description: "walrus in class-body comprehension stays valid syntax",
            source: "values = [item for item in range(3)]\n",
            python_minor: 12,
            expected_valid: true,
            expected_failure_line: 0,
        },
    ];

    for test_case in &test_cases {
        let version = PythonVersion {
            major: 3,
            minor: test_case.python_minor,
        };
        let outcome = parse_strict(test_case.source, version);
        let failure_line = outcome.as_ref().err().map(|failure| failure.line);

        assert_eq!(
            outcome.is_ok(),
            test_case.expected_valid,
            "case failed: {}",
            test_case.description
        );
        assert_eq!(
            failure_line.unwrap_or_default(),
            test_case.expected_failure_line,
            "case failed: {}",
            test_case.description
        );
    }
}
