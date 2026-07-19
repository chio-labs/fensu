//! Immutable native memory tuple conversion contracts.

use pyo3::types::PyAnyMethods;
use pyo3::Python;

use crate::extension::helpers::memory_conversion::test_types::{
    SchemaConversionTestCase, SummaryConversionTestCase,
};
use crate::extension::helpers::memory_conversion::{
    memory_overview_object, memory_relation_schema_object, memory_schema_object,
    sync_summary_object,
};
use fensu_memory::engine::main::memory_relation_schema::memory_relation_schema;
use fensu_memory::engine::main::memory_schema::memory_schema;
use fensu_memory::engine::models::{MemoryOverview, SyncSummary};

#[test]
fn given_sync_and_overview_models_when_converting_then_tuple_field_order_is_stable() {
    let test_cases = [SummaryConversionTestCase {
        description: "sync and overview fields retain their documented tuple positions",
        expected_sync: (1, 2, 3, 4, 5, true, false, 6, 7, 8),
        expected_overview: (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12),
    }];
    Python::initialize();
    for test_case in &test_cases {
        Python::attach(|py| {
            let sync = sync_summary_object(
                py,
                SyncSummary {
                    added_count: 1,
                    changed_count: 2,
                    moved_count: 3,
                    removed_count: 4,
                    unchanged_count: 5,
                    rebuilt: true,
                    changed: false,
                    document_count: 6,
                    section_count: 7,
                    link_count: 8,
                },
            )
            .expect("sync conversion succeeds");
            let sync_values = sync
                .bind(py)
                .extract::<(
                    usize,
                    usize,
                    usize,
                    usize,
                    usize,
                    bool,
                    bool,
                    usize,
                    usize,
                    usize,
                )>()
                .expect("sync tuple extracts");
            let overview = memory_overview_object(
                py,
                MemoryOverview {
                    not_started_task_count: 1,
                    in_progress_task_count: 2,
                    completed_task_count: 3,
                    cancelled_task_count: 4,
                    superseded_task_count: 5,
                    active_note_count: 6,
                    active_decision_count: 7,
                    active_skill_count: 8,
                    archived_task_count: 9,
                    archived_knowledge_count: 10,
                    document_count: 11,
                    section_count: 12,
                },
            )
            .expect("overview conversion succeeds");
            let overview_values = overview
                .bind(py)
                .extract::<(
                    usize,
                    usize,
                    usize,
                    usize,
                    usize,
                    usize,
                    usize,
                    usize,
                    usize,
                    usize,
                    usize,
                    usize,
                )>()
                .expect("overview tuple extracts");
            assert_eq!(
                sync_values, test_case.expected_sync,
                "{}",
                test_case.description
            );
            assert_eq!(
                overview_values, test_case.expected_overview,
                "{}",
                test_case.description
            );
        });
    }
}

#[test]
fn given_schema_models_when_converting_then_nested_tuples_are_immutable_and_precise() {
    let test_cases = [SchemaConversionTestCase {
        description: "schema overview and focused columns use nested immutable tuples",
        expected_versions: (1, 1),
        expected_relation_count: 20,
        expected_first_relation: "memory.documents",
        expected_focused_relation: "memory.current_tasks",
        expected_focused_kind: "view",
        expected_first_column: "identity",
        expected_first_type: "VARCHAR",
    }];
    Python::initialize();
    for test_case in &test_cases {
        Python::attach(|py| {
            let schema =
                memory_schema_object(py, memory_schema()).expect("schema conversion succeeds");
            let values = schema
                .bind(py)
                .extract::<(u32, u32, Vec<(String, String, String)>)>()
                .expect("schema tuple extracts");
            let relation = memory_relation_schema("memory.current_tasks").expect("relation exists");
            let object =
                memory_relation_schema_object(py, relation).expect("relation conversion succeeds");
            let focused = object
                .bind(py)
                .extract::<(String, String, String, Vec<(String, String, bool, String)>)>()
                .expect("relation tuple extracts");
            assert_eq!(
                (values.0, values.1),
                test_case.expected_versions,
                "{}",
                test_case.description
            );
            assert_eq!(
                values.2.len(),
                test_case.expected_relation_count,
                "{}",
                test_case.description
            );
            assert_eq!(
                values.2[0].0, test_case.expected_first_relation,
                "{}",
                test_case.description
            );
            assert_eq!(
                focused.0, test_case.expected_focused_relation,
                "{}",
                test_case.description
            );
            assert_eq!(
                focused.1, test_case.expected_focused_kind,
                "{}",
                test_case.description
            );
            assert_eq!(
                focused.3[0].0, test_case.expected_first_column,
                "{}",
                test_case.description
            );
            assert_eq!(
                focused.3[0].1, test_case.expected_first_type,
                "{}",
                test_case.description
            );
        });
    }
}
