//! Cached-generation replay observation contracts.

use std::collections::HashMap;
use std::path::Path;

use crate::cache::_helpers::replay::{observe_dependencies, python_path_matches};
use crate::cache::constants::PROJECT_REQUESTER_PATH;
use crate::cache::models::{CanonicalValue, NativeDependencyKey, NativeDependencyObservation};
use crate::cache::tests::_helpers::{keyed_graph_snapshot, scalar_graph_snapshot};
use crate::cache::tests::test_types::{ReplayObservationTestCase, TreeGlobTestCase};

#[test]
fn given_graph_observations_when_replaying_then_snapshot_answers_are_compared() {
    let answer = CanonicalValue::String("[]".to_owned());
    let test_cases = [
        ReplayObservationTestCase {
            description: "dependency answer uses the graph root",
            query_path: "src/example/entry.py",
            kind: "graph_dependencies",
            root_prefix: ".",
            snapshot: keyed_graph_snapshot("src/example/entry.py", ".", "dependencies", &answer),
            expected_current: true,
        },
        ReplayObservationTestCase {
            description: "cycle answer uses an explicit nested root",
            query_path: "workspace",
            kind: "graph_cycles",
            root_prefix: "workspace",
            snapshot: scalar_graph_snapshot("workspace", "cycles", &answer),
            expected_current: true,
        },
    ];

    for test_case in test_cases {
        let key = NativeDependencyKey {
            query_path: test_case.query_path.to_owned(),
            kind: test_case.kind.to_owned(),
            pattern: None,
            recursive: false,
        };
        let observations = HashMap::from([(
            key.clone(),
            NativeDependencyObservation {
                requester_path: PROJECT_REQUESTER_PATH.to_owned(),
                key: key.clone(),
                dependency_path: test_case.root_prefix.to_owned(),
                answer: answer.clone(),
            },
        )]);

        assert_eq!(
            observe_dependencies(Path::new("."), &observations, Some(&test_case.snapshot)),
            HashMap::from([(key, test_case.expected_current)]),
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_tree_globs_when_matching_then_pure_path_double_star_semantics_are_preserved() {
    let test_cases = [
        TreeGlobTestCase {
            description: "root file does not satisfy leading double star",
            path: "entry.py",
            pattern: "**/*.py",
            expected_match: false,
        },
        TreeGlobTestCase {
            description: "nested file satisfies leading double star",
            path: "src/entry.py",
            pattern: "**/*.py",
            expected_match: true,
        },
        TreeGlobTestCase {
            description: "direct child does not satisfy middle double star",
            path: "src/entry.py",
            pattern: "src/**/*.py",
            expected_match: false,
        },
        TreeGlobTestCase {
            description: "one nested segment satisfies middle double star",
            path: "src/orders/entry.py",
            pattern: "src/**/*.py",
            expected_match: true,
        },
        TreeGlobTestCase {
            description: "multiple nested segments do not satisfy one normalized segment",
            path: "src/orders/main/entry.py",
            pattern: "src/**/*.py",
            expected_match: false,
        },
    ];

    for test_case in test_cases {
        assert_eq!(
            python_path_matches(test_case.path, test_case.pattern),
            test_case.expected_match,
            "{}",
            test_case.description
        );
    }
}
