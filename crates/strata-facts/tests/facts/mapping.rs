//! Native mapping-substrate extraction tests.

use ruff_python_ast::PythonVersion;
use strata_facts::facts::mapping::main::extract_mapping_declarations::extract_mapping_declarations;
use strata_facts::facts::mapping::main::extract_mapping_facts::extract_mapping_facts;
use strata_facts::parsing::main::parse_strict::parse_strict;
use strata_facts::positions::main::index_lines::index_lines;

use crate::test_types;

#[test]
fn given_project_functions_and_local_calls_when_extracting_then_preserves_map_state() {
    let test_cases = [test_types::MappingRowsTestCase {
        description: "declarations and local calls retain map state",
        source: "from typing import TYPE_CHECKING\nfrom pkg.workers import Worker\n\nif TYPE_CHECKING:\n    from pkg.contracts import Runner\n\nclass Owner:\n    helper: Worker\n\n    def execute(self, runner: Runner) -> Worker:\n        worker = Worker()\n        worker.prepare()\n        runner.execute()\n        return worker\n",
        expected_declaration_function_count: 1,
        expected_class_name: "Owner",
        expected_annotation_import_count: 3,
        expected_parameter_name: "runner",
        expected_binding_name: Some("worker"),
        expected_calls: &["Worker", "worker.prepare", "runner.execute"],
    }];
    for test_case in test_cases {
        let version = PythonVersion {
            major: 3,
            minor: 12,
        };
        let parsed = parse_strict(test_case.source, version).expect(test_case.description);
        let index = index_lines(test_case.source);
        let declarations = extract_mapping_declarations(parsed.syntax(), &index, test_case.source);
        let complete = extract_mapping_facts(parsed.syntax(), &index, test_case.source);
        let calls = complete.functions[0]
            .statements
            .iter()
            .flat_map(|statement| &statement.calls)
            .map(|call| call.callee.spelling.as_str())
            .collect::<Vec<_>>();

        assert_eq!(
            declarations.functions.len(),
            test_case.expected_declaration_function_count,
            "{}",
            test_case.description
        );
        assert!(
            declarations.functions[0].statements.is_empty(),
            "{}",
            test_case.description
        );
        assert_eq!(
            declarations.classes[0].name, test_case.expected_class_name,
            "{}",
            test_case.description
        );
        assert_eq!(
            declarations.annotation_imports.len(),
            test_case.expected_annotation_import_count,
            "{}",
            test_case.description
        );
        assert_eq!(
            complete.functions[0].parameters[1].name, test_case.expected_parameter_name,
            "{}",
            test_case.description
        );
        assert_eq!(
            complete.functions[0].statements[0].binding_name.as_deref(),
            test_case.expected_binding_name,
            "{}",
            test_case.description
        );
        assert_eq!(calls, test_case.expected_calls, "{}", test_case.description);
    }
}
