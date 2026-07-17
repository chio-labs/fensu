//! Direct row extraction tests for public rule-authoring families.

use ruff_python_ast::PythonVersion;
use strata_facts::facts::main::extract_class_declarations::extract_class_declarations;
use strata_facts::facts::main::extract_parameter_mutation_occurrences::extract_parameter_mutation_occurrences;
use strata_facts::facts::main::extract_parameter_mutations::extract_parameter_mutations;
use strata_facts::facts::main::extract_rule_calls::extract_rule_calls;
use strata_facts::facts::main::extract_rule_references::extract_rule_references;
use strata_facts::facts::types::LiteralValueRow;
use strata_facts::parsing::main::parse_strict::parse_strict;
use strata_facts::positions::main::index_lines::index_lines;

use crate::test_types;

#[test]
fn given_rule_authoring_shapes_when_extracting_rows_then_preserves_public_semantics() {
    let test_cases = [test_types::RuleAuthoringRowsTestCase {
        description: "all six public rule-authoring row families",
        class_source: "@registry.wrap(flag=True)\nclass Outer(pkg.Base[T], factory()):\n    def first(self): pass\n    class Inner(Outer):\n        async def second(self): pass\n",
        assignment_source: "class Box:\n    def method(self):\n        left, (right, *rest) = source.item\n        obj.attr = package.other\n        nested = factory().result\n",
        call_source: "def outer():\n    for item in rows:\n        def inner():\n            service.call('x', dynamic, b'\\xff', 340282366920938463463374607431768211457, 1.5, 2j, True, None, ...)\n    super()\n    assigned = factory().result()\n",
        edge_source: "class Worker:\n    def outer(self):\n        def inner():\n            while ready:\n                target.part()\n",
        comparison_source: "if pkg.value == compute() < rows[index] != factory().attr:\n    pass\nif SqlReferenceKind[T].DBT_REF == kind:\n    pass\nif factory().SqlReferenceKind.DBT_REF == kind:\n    pass\nif make_kind().DBT_REF == kind:\n    pass\n",
        mutation_source: "def kinds(pos_only, /, normal, *extra, named, **rest):\n    pos_only.append(1)\n    normal.append(1)\n    extra.append(1)\n    named.append(1)\n    rest.update({})\nclass Box:\n    @value.setter\n    def value(self, items):\n        items.append(1)\n        items.append(2)\n        return items\n",
        expected_class_names: &["Outer", "Inner"],
        expected_base_name: "Base",
        expected_method_names: &["first", "second"],
        expected_target_names: &["left", "right", "rest"],
        expected_assignment_reference: "source.item",
        expected_call_names: &[Some("super"), Some("result"), Some("service.call"), Some("factory")],
        expected_function_chain: &["inner", "outer"],
        expected_literal_position: 2,
        expected_literal_source: "'x'",
        expected_bytes: &[255],
        expected_integer: "340282366920938463463374607431768211457",
        expected_edge_callers: &["inner", "outer"],
        expected_comparison_operand_count: 4,
        expected_reference_receivers: &[Some("SqlReferenceKind"), Some("SqlReferenceKind"), None],
        expected_reference_parts: &[&["SqlReferenceKind", "DBT_REF"], &[], &[]],
        expected_mutation_lines: &[2, 3, 4, 5, 6, 10, 11],
        expected_mutation_kinds: &[
            "positional_only",
            "positional_or_keyword",
            "vararg",
            "keyword_only",
            "kwarg",
            "positional_or_keyword",
            "positional_or_keyword",
        ],
        expected_first_only_count: 6,
    }];
    for test_case in test_cases {
        let version = PythonVersion {
            major: 3,
            minor: 12,
        };
        let class_parsed = parse_strict(test_case.class_source, version).expect("class source");
        let class_rows = extract_class_declarations(
            class_parsed.syntax(),
            &index_lines(test_case.class_source),
            test_case.class_source,
        );
        assert_eq!(
            class_rows
                .iter()
                .map(|row| row.name.as_str())
                .collect::<Vec<_>>(),
            test_case.expected_class_names,
            "{}",
            test_case.description
        );
        assert_eq!(
            class_rows[0].base_names[0], test_case.expected_base_name,
            "{}",
            test_case.description
        );
        assert_eq!(
            class_rows
                .iter()
                .map(|row| row.methods[0].name.as_str())
                .collect::<Vec<_>>(),
            test_case.expected_method_names,
            "{}",
            test_case.description
        );

        let assignment_parsed =
            parse_strict(test_case.assignment_source, version).expect("assignment source");
        let (assignment_rows, _) = extract_rule_references(
            assignment_parsed.syntax(),
            &index_lines(test_case.assignment_source),
            test_case.assignment_source,
        );
        assert_eq!(
            assignment_rows[0].target_names, test_case.expected_target_names,
            "{}",
            test_case.description
        );
        assert_eq!(
            assignment_rows[0]
                .value_reference
                .as_ref()
                .and_then(|row| row.name.as_deref()),
            Some(test_case.expected_assignment_reference),
            "{}",
            test_case.description
        );

        let call_parsed = parse_strict(test_case.call_source, version).expect("call source");
        let (call_rows, _) = extract_rule_calls(
            call_parsed.syntax(),
            &index_lines(test_case.call_source),
            test_case.call_source,
        );
        assert_eq!(
            call_rows
                .iter()
                .map(|row| row.name.as_deref())
                .collect::<Vec<_>>(),
            test_case.expected_call_names,
            "{}",
            test_case.description
        );
        assert_eq!(
            call_rows[2]
                .enclosing_functions
                .iter()
                .map(|row| row.name.as_str())
                .collect::<Vec<_>>(),
            test_case.expected_function_chain,
            "{}",
            test_case.description
        );
        assert_eq!(
            call_rows[2].literal_arguments[0].value,
            LiteralValueRow::StringSource(test_case.expected_literal_source.to_owned()),
            "{}",
            test_case.description
        );
        assert_eq!(
            call_rows[2].literal_arguments[1].position, test_case.expected_literal_position,
            "{}",
            test_case.description
        );
        assert_eq!(
            call_rows[2].literal_arguments[1].value,
            LiteralValueRow::Bytes(test_case.expected_bytes.to_vec()),
            "{}",
            test_case.description
        );
        assert_eq!(
            call_rows[2].literal_arguments[2].value,
            LiteralValueRow::Integer(test_case.expected_integer.to_owned()),
            "{}",
            test_case.description
        );

        let edge_parsed = parse_strict(test_case.edge_source, version).expect("edge source");
        let (_, edge_rows) = extract_rule_calls(
            edge_parsed.syntax(),
            &index_lines(test_case.edge_source),
            test_case.edge_source,
        );
        assert_eq!(
            edge_rows
                .iter()
                .map(|row| row.caller.name.as_str())
                .collect::<Vec<_>>(),
            test_case.expected_edge_callers,
            "{}",
            test_case.description
        );

        let comparison_parsed =
            parse_strict(test_case.comparison_source, version).expect("comparison source");
        let (_, comparison_rows) = extract_rule_references(
            comparison_parsed.syntax(),
            &index_lines(test_case.comparison_source),
            test_case.comparison_source,
        );
        assert_eq!(
            comparison_rows[0].operand_references.len(),
            test_case.expected_comparison_operand_count,
            "{}",
            test_case.description
        );
        assert_eq!(
            comparison_rows[1..]
                .iter()
                .map(|row| {
                    row.operand_references[0]
                        .as_ref()
                        .and_then(|reference| reference.receiver_base_name.as_deref())
                })
                .collect::<Vec<_>>(),
            test_case.expected_reference_receivers,
            "{}",
            test_case.description
        );
        assert_eq!(
            comparison_rows[1..]
                .iter()
                .map(|row| {
                    row.operand_references[0]
                        .as_ref()
                        .map(|reference| {
                            reference
                                .parts
                                .iter()
                                .map(String::as_str)
                                .collect::<Vec<_>>()
                        })
                        .unwrap_or_default()
                })
                .collect::<Vec<_>>(),
            test_case.expected_reference_parts,
            "{}",
            test_case.description
        );

        let mutation_parsed =
            parse_strict(test_case.mutation_source, version).expect("mutation source");
        let mutation_index = index_lines(test_case.mutation_source);
        let mutation_rows = extract_parameter_mutation_occurrences(
            mutation_parsed.syntax(),
            &mutation_index,
            test_case.mutation_source,
        );
        let first_rows = extract_parameter_mutations(
            mutation_parsed.syntax(),
            &mutation_index,
            test_case.mutation_source,
        );
        assert_eq!(
            mutation_rows.iter().map(|row| row.line).collect::<Vec<_>>(),
            test_case.expected_mutation_lines,
            "{}",
            test_case.description
        );
        assert_eq!(
            mutation_rows
                .iter()
                .map(|row| row.parameter_kind.as_str())
                .collect::<Vec<_>>(),
            test_case.expected_mutation_kinds,
            "{}",
            test_case.description
        );
        assert_eq!(
            first_rows.len(),
            test_case.expected_first_only_count,
            "{}",
            test_case.description
        );
    }
}
