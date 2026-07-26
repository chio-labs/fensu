//! Task dependency state and cycle behavior.

use crate::helpers;
use crate::test_types::{DependencyGraphTestCase, ExpectedDependencyEdge, FixtureFile};
use fensu_memory::graph::types::{DependencyState, GraphDiagnosticKind};

#[test]
fn given_task_relationships_when_building_graph_then_classifies_dependencies_and_reports_cycles() {
    let test_cases = [DependencyGraphTestCase {
        description: "classifies active, archived, terminal, broken, self, and cyclic dependencies",
        files: &[
            FixtureFile {
                path: ".ai/tasks/in-progress/20260717T200000_000000Z__FEAT-source-task.md",
                contents: "# Source Task\n\n- depends-on: [[completed-target]]\n- depends-on: [[archived-completed]]\n- depends-on: [[not-started-target]]\n- depends-on: [[in-progress-target]]\n- depends-on: [[cancelled-target]]\n- depends-on: [[superseded-target]]\n- depends-on: [[note-target]]\n- depends-on: [[missing-target]]\n- depends-on: [[duplicate-dep]]\n- depends-on: [[task:20260717T200000_000000Z]]\n",
            },
            FixtureFile {
                path: ".ai/tasks/completed/20260717T200001_000000Z__FEAT-completed-target.md",
                contents: "# Completed Target\n",
            },
            FixtureFile {
                path: ".ai/_archive/tasks/completed/20260717T200002_000000Z__FEAT-archived-completed.md",
                contents: "# Archived Completed\n",
            },
            FixtureFile {
                path: ".ai/tasks/not-started/20260717T200003_000000Z__FEAT-not-started-target.md",
                contents: "# Not Started Target\n",
            },
            FixtureFile {
                path: ".ai/tasks/in-progress/20260717T200004_000000Z__FEAT-in-progress-target.md",
                contents: "# In Progress Target\n",
            },
            FixtureFile {
                path: ".ai/tasks/cancelled/20260717T200005_000000Z__FEAT-cancelled-target.md",
                contents: "# Cancelled Target\n",
            },
            FixtureFile {
                path: ".ai/tasks/superseded/20260717T200006_000000Z__FEAT-superseded-target.md",
                contents: "# Superseded Target\n",
            },
            FixtureFile {
                path: ".ai/knowledge/repo/notes/20260717T200007_000000Z__NOTE-note-target.md",
                contents: "# Note Target\n",
            },
            FixtureFile {
                path: ".ai/tasks/not-started/20260717T200008_000000Z__FEAT-duplicate-dep.md",
                contents: "# Duplicate One\n",
            },
            FixtureFile {
                path: ".ai/tasks/in-progress/20260717T200009_000000Z__FEAT-duplicate-dep.md",
                contents: "# Duplicate Two\n",
            },
            FixtureFile {
                path: ".ai/tasks/in-progress/20260717T200010_000000Z__FEAT-cycle-a.md",
                contents: "# Cycle A\n\n- depends-on: [[cycle-b]]\n",
            },
            FixtureFile {
                path: ".ai/tasks/in-progress/20260717T200011_000000Z__FEAT-cycle-b.md",
                contents: "# Cycle B\n\n- depends-on: [[cycle-c]]\n",
            },
            FixtureFile {
                path: ".ai/tasks/in-progress/20260717T200012_000000Z__FEAT-cycle-c.md",
                contents: "# Cycle C\n\n- depends-on: [[cycle-a]]\n",
            },
            FixtureFile {
                path: ".ai/knowledge/repo/notes/20260717T200013_000000Z__NOTE-non-task-source.md",
                contents: "# Non Task Source\n\n- depends-on: [[completed-target]]\n",
            },
        ],
        expected_edges: &[
            ExpectedDependencyEdge {
                source_identity: "task:20260717T200000_000000Z",
                ordinal: 1,
                expected_target_identity: Some("task:20260717T200001_000000Z"),
                expected_state: DependencyState::Satisfied,
            },
            ExpectedDependencyEdge {
                source_identity: "task:20260717T200000_000000Z",
                ordinal: 2,
                expected_target_identity: Some("task:20260717T200002_000000Z"),
                expected_state: DependencyState::Satisfied,
            },
            ExpectedDependencyEdge {
                source_identity: "task:20260717T200000_000000Z",
                ordinal: 3,
                expected_target_identity: Some("task:20260717T200003_000000Z"),
                expected_state: DependencyState::Blocking,
            },
            ExpectedDependencyEdge {
                source_identity: "task:20260717T200000_000000Z",
                ordinal: 4,
                expected_target_identity: Some("task:20260717T200004_000000Z"),
                expected_state: DependencyState::Blocking,
            },
            ExpectedDependencyEdge {
                source_identity: "task:20260717T200000_000000Z",
                ordinal: 5,
                expected_target_identity: Some("task:20260717T200005_000000Z"),
                expected_state: DependencyState::Unresolved,
            },
            ExpectedDependencyEdge {
                source_identity: "task:20260717T200000_000000Z",
                ordinal: 6,
                expected_target_identity: Some("task:20260717T200006_000000Z"),
                expected_state: DependencyState::Unresolved,
            },
            ExpectedDependencyEdge {
                source_identity: "task:20260717T200000_000000Z",
                ordinal: 7,
                expected_target_identity: Some("note:20260717T200007_000000Z"),
                expected_state: DependencyState::Unresolved,
            },
            ExpectedDependencyEdge {
                source_identity: "task:20260717T200000_000000Z",
                ordinal: 8,
                expected_target_identity: None,
                expected_state: DependencyState::Unresolved,
            },
            ExpectedDependencyEdge {
                source_identity: "task:20260717T200000_000000Z",
                ordinal: 9,
                expected_target_identity: None,
                expected_state: DependencyState::Unresolved,
            },
            ExpectedDependencyEdge {
                source_identity: "task:20260717T200000_000000Z",
                ordinal: 10,
                expected_target_identity: Some("task:20260717T200000_000000Z"),
                expected_state: DependencyState::Blocking,
            },
            ExpectedDependencyEdge {
                source_identity: "task:20260717T200010_000000Z",
                ordinal: 1,
                expected_target_identity: Some("task:20260717T200011_000000Z"),
                expected_state: DependencyState::Blocking,
            },
            ExpectedDependencyEdge {
                source_identity: "task:20260717T200011_000000Z",
                ordinal: 1,
                expected_target_identity: Some("task:20260717T200012_000000Z"),
                expected_state: DependencyState::Blocking,
            },
            ExpectedDependencyEdge {
                source_identity: "task:20260717T200012_000000Z",
                ordinal: 1,
                expected_target_identity: Some("task:20260717T200010_000000Z"),
                expected_state: DependencyState::Blocking,
            },
        ],
        expected_dependency_diagnostics: &[
            GraphDiagnosticKind::SelfDependency,
            GraphDiagnosticKind::DependencyCycle,
        ],
        expected_cycle_identities: &[
            "task:20260717T200010_000000Z",
            "task:20260717T200011_000000Z",
            "task:20260717T200012_000000Z",
        ],
    }];

    for test_case in &test_cases {
        let (root, graph) = helpers::load_graph(test_case.files);
        assert_eq!(
            graph.dependencies.len(),
            test_case.expected_edges.len(),
            "{}",
            test_case.description
        );
        for (actual, expected) in graph.dependencies.iter().zip(test_case.expected_edges) {
            assert_eq!(
                actual.source_document_identity.0, expected.source_identity,
                "{}",
                test_case.description
            );
            assert_eq!(
                actual.source_link_ordinal, expected.ordinal,
                "{}",
                test_case.description
            );
            assert_eq!(
                actual
                    .target_document_identity
                    .as_ref()
                    .map(|identity| identity.0.as_str()),
                expected.expected_target_identity,
                "{}",
                test_case.description
            );
            assert_eq!(
                actual.state, expected.expected_state,
                "{}",
                test_case.description
            );
        }
        let dependency_diagnostics: Vec<GraphDiagnosticKind> = graph
            .diagnostics
            .iter()
            .filter(|diagnostic| {
                matches!(
                    diagnostic.kind,
                    GraphDiagnosticKind::SelfDependency | GraphDiagnosticKind::DependencyCycle
                )
            })
            .map(|diagnostic| diagnostic.kind)
            .collect();
        assert_eq!(
            dependency_diagnostics, test_case.expected_dependency_diagnostics,
            "{}",
            test_case.description
        );
        let cycle_identities: Vec<&str> = graph
            .diagnostics
            .iter()
            .find(|diagnostic| diagnostic.kind == GraphDiagnosticKind::DependencyCycle)
            .expect("three-node cycle emits a diagnostic")
            .target_document_identities
            .iter()
            .map(|identity| identity.0.as_str())
            .collect();
        assert_eq!(
            cycle_identities, test_case.expected_cycle_identities,
            "{}",
            test_case.description
        );
        helpers::remove_temp_tree(&root);
    }
}
