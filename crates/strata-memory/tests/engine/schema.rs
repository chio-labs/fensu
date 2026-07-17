//! Frozen schema overview and focused relation metadata.

use strata_memory::engine::main::memory_relation_schema::memory_relation_schema;
use strata_memory::engine::main::memory_schema::memory_schema;

use crate::test_types::MemorySchemaTestCase;

#[test]
fn given_compiled_schema_when_introspecting_then_returns_qualified_relations_and_columns() {
    let test_cases = [MemorySchemaTestCase {
        description: "compiled metadata names the public catalog and focused columns",
        expected_versions: (1, 1),
        expected_relation_count: 20,
        expected_relation_name: "memory.archived_tasks",
        expected_focused: ("memory.current_tasks", "view", 20),
        expected_first_column: ("identity", "VARCHAR", false, "Stable document identity."),
    }];
    for test_case in &test_cases {
        let schema = memory_schema();
        let names = schema
            .relations
            .iter()
            .map(|relation| relation.name)
            .collect::<Vec<&str>>();
        let relation = memory_relation_schema("memory.current_tasks").expect("relation exists");
        assert_eq!(
            (schema.schema_version, schema.parser_contract_version),
            test_case.expected_versions,
            "{}",
            test_case.description
        );
        assert_eq!(
            schema.relations.len(),
            test_case.expected_relation_count,
            "{}",
            test_case.description
        );
        assert!(
            names.contains(&test_case.expected_relation_name),
            "{}",
            test_case.description
        );
        assert_eq!(
            (relation.name, relation.kind, relation.columns.len()),
            test_case.expected_focused,
            "{}",
            test_case.description
        );
        assert_eq!(
            (
                relation.columns[0].name,
                relation.columns[0].data_type,
                relation.columns[0].nullable,
                relation.columns[0].comment,
            ),
            test_case.expected_first_column,
            "{}",
            test_case.description
        );
        assert_eq!(
            memory_relation_schema("current_tasks"),
            Some(relation),
            "{}",
            test_case.description
        );
        assert_eq!(
            memory_relation_schema("memory.unknown"),
            None,
            "{}",
            test_case.description
        );
    }
}
