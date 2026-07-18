//! Bounded read-only memory graph query behavior.

use std::fs;

use strata_memory::engine::main::query_memory_graph::query_memory_graph;
use strata_memory::engine::main::rebuild_memory_index::rebuild_memory_index;
use strata_memory::engine::models::{
    MemoryGraphDirection, MemoryGraphQuery, MemoryGraphRelationship,
};

use crate::dependencies::helpers;
use crate::test_types::{FixtureFile, InvalidMemoryGraphTestCase, MemoryGraphTraversalTestCase};

const ALPHA: &str = "note:20260718T100001_000000Z";
const BETA: &str = "note:20260718T100002_000000Z";
const GAMMA: &str = "note:20260718T100003_000000Z";
const ARCHIVED: &str = "note:20260718T100004_000000Z";
const DELTA: &str = "note:20260718T100005_000000Z";
const RELATED: &[MemoryGraphRelationship] = &[MemoryGraphRelationship::Related];
const FILES: &[FixtureFile] = &[
    FixtureFile {
        path: ".ai/knowledge/repo/notes/20260718T100001_000000Z__NOTE-alpha.md",
        contents: b"# Alpha\n\n[[beta]]\n\n- related: [[gamma]]\n\n[[archived]]\n\n[external](https://example.com)\n\n[[missing]]\n",
    },
    FixtureFile {
        path: ".ai/knowledge/repo/notes/20260718T100002_000000Z__NOTE-beta.md",
        contents: b"# Beta\n\n[[alpha]]\n",
    },
    FixtureFile {
        path: ".ai/knowledge/repo/notes/20260718T100003_000000Z__NOTE-gamma.md",
        contents: b"# Gamma\n",
    },
    FixtureFile {
        path: ".ai/_archive/knowledge/repo/notes/20260718T100004_000000Z__NOTE-archived.md",
        contents: b"# Archived\n\n[[delta]]\n",
    },
    FixtureFile {
        path: ".ai/knowledge/repo/notes/20260718T100005_000000Z__NOTE-delta.md",
        contents: b"# Delta\n",
    },
    FixtureFile {
        path: ".ai/knowledge/repo/notes/20260718T100006_000000Z__NOTE-duplicate-one.md",
        contents: b"# Duplicate\n",
    },
    FixtureFile {
        path: ".ai/knowledge/repo/notes/20260718T100007_000000Z__NOTE-duplicate-two.md",
        contents: b"# Duplicate\n",
    },
];

#[test]
fn given_graph_queries_when_traversing_then_applies_direction_filters_archives_and_budgets() {
    let test_cases = [
        MemoryGraphTraversalTestCase {
            description: "outbound traversal retains leaves cycles and archived targets",
            pattern: ALPHA,
            direction: MemoryGraphDirection::Outbound,
            relationships: &[],
            depth: 2,
            max_nodes: 50,
            max_edges: 100,
            include_archived: false,
            expected_selection: "exact",
            expected_roots: &[ALPHA],
            expected_nodes: &[ALPHA, BETA, GAMMA, ARCHIVED],
            expected_edge_count: 6,
            expected_node_exhausted: false,
            expected_edge_exhausted: false,
        },
        MemoryGraphTraversalTestCase {
            description: "inbound traversal follows authored edges in reverse",
            pattern: ALPHA,
            direction: MemoryGraphDirection::Inbound,
            relationships: &[],
            depth: 1,
            max_nodes: 50,
            max_edges: 100,
            include_archived: false,
            expected_selection: "exact",
            expected_roots: &[ALPHA],
            expected_nodes: &[ALPHA, BETA],
            expected_edge_count: 1,
            expected_node_exhausted: false,
            expected_edge_exhausted: false,
        },
        MemoryGraphTraversalTestCase {
            description: "relationship filtering excludes generic links",
            pattern: "Alp",
            direction: MemoryGraphDirection::Both,
            relationships: RELATED,
            depth: 2,
            max_nodes: 50,
            max_edges: 100,
            include_archived: false,
            expected_selection: "substring",
            expected_roots: &[ALPHA],
            expected_nodes: &[ALPHA, GAMMA],
            expected_edge_count: 1,
            expected_node_exhausted: false,
            expected_edge_exhausted: false,
        },
        MemoryGraphTraversalTestCase {
            description: "archived roots and descendants expand only when requested",
            pattern: ARCHIVED,
            direction: MemoryGraphDirection::Outbound,
            relationships: &[],
            depth: 2,
            max_nodes: 50,
            max_edges: 100,
            include_archived: true,
            expected_selection: "exact",
            expected_roots: &[ARCHIVED],
            expected_nodes: &[ARCHIVED, DELTA],
            expected_edge_count: 1,
            expected_node_exhausted: false,
            expected_edge_exhausted: false,
        },
        MemoryGraphTraversalTestCase {
            description: "node budget leaves resolved targets omitted and reports exhaustion",
            pattern: ALPHA,
            direction: MemoryGraphDirection::Outbound,
            relationships: &[],
            depth: 5,
            max_nodes: 1,
            max_edges: 100,
            include_archived: false,
            expected_selection: "exact",
            expected_roots: &[ALPHA],
            expected_nodes: &[ALPHA],
            expected_edge_count: 5,
            expected_node_exhausted: true,
            expected_edge_exhausted: false,
        },
        MemoryGraphTraversalTestCase {
            description: "edge budget truncates deterministically and reports exhaustion",
            pattern: ALPHA,
            direction: MemoryGraphDirection::Outbound,
            relationships: &[],
            depth: 5,
            max_nodes: 50,
            max_edges: 1,
            include_archived: false,
            expected_selection: "exact",
            expected_roots: &[ALPHA],
            expected_nodes: &[ALPHA, BETA],
            expected_edge_count: 1,
            expected_node_exhausted: false,
            expected_edge_exhausted: true,
        },
    ];
    let root = helpers::write_repository(FILES);
    let database_path = root.join("memory.sqlite3");
    rebuild_memory_index(&root, &database_path).expect("graph fixture publishes");
    for test_case in &test_cases {
        let result = query_memory_graph(
            &database_path,
            &MemoryGraphQuery {
                pattern: test_case.pattern.to_owned(),
                direction: test_case.direction,
                relationships: test_case.relationships.to_vec(),
                depth: test_case.depth,
                max_nodes: test_case.max_nodes,
                max_edges: test_case.max_edges,
                include_archived: test_case.include_archived,
            },
        )
        .expect(test_case.description);
        assert_eq!(
            result.selection, test_case.expected_selection,
            "{}",
            test_case.description
        );
        assert_eq!(
            result.roots, test_case.expected_roots,
            "{}",
            test_case.description
        );
        assert_eq!(
            result
                .nodes
                .iter()
                .map(|node| node.identity.as_str())
                .collect::<Vec<&str>>(),
            test_case.expected_nodes,
            "{}",
            test_case.description
        );
        assert_eq!(
            result.edges.len(),
            test_case.expected_edge_count,
            "{}",
            test_case.description
        );
        assert_eq!(
            result.node_budget_exhausted, test_case.expected_node_exhausted,
            "{}",
            test_case.description
        );
        assert_eq!(
            result.edge_budget_exhausted, test_case.expected_edge_exhausted,
            "{}",
            test_case.description
        );
    }
    let full = query_memory_graph(
        &database_path,
        &MemoryGraphQuery {
            pattern: ALPHA.to_owned(),
            direction: MemoryGraphDirection::Outbound,
            relationships: Vec::new(),
            depth: 2,
            max_nodes: 50,
            max_edges: 100,
            include_archived: false,
        },
    )
    .expect("full graph query succeeds");
    assert!(full
        .edges
        .iter()
        .any(|edge| edge.resolution_status == "external"));
    assert!(full
        .edges
        .iter()
        .any(|edge| edge.resolution_status == "unresolved"));
    assert!(full.edges.iter().any(|edge| edge.cycle));
    fs::remove_dir_all(root).expect("graph fixture is removable");
}

#[test]
fn given_invalid_or_ambiguous_graph_selectors_when_querying_then_fails_clearly() {
    let test_cases = [
        InvalidMemoryGraphTestCase {
            description: "ambiguous exact title is rejected",
            pattern: "Duplicate",
            depth: 2,
            max_nodes: 50,
            max_edges: 100,
            include_archived: false,
            expected_error_fragment: "exactly matches multiple documents",
        },
        InvalidMemoryGraphTestCase {
            description: "missing selector is rejected",
            pattern: "not-present",
            depth: 2,
            max_nodes: 50,
            max_edges: 100,
            include_archived: false,
            expected_error_fragment: "no memory documents match",
        },
        InvalidMemoryGraphTestCase {
            description: "archived root explains opt-in",
            pattern: ARCHIVED,
            depth: 2,
            max_nodes: 50,
            max_edges: 100,
            include_archived: false,
            expected_error_fragment: "use --include-archived",
        },
        InvalidMemoryGraphTestCase {
            description: "depth lower hard bound is enforced natively",
            pattern: ALPHA,
            depth: 0,
            max_nodes: 50,
            max_edges: 100,
            include_archived: false,
            expected_error_fragment: "depth 0 is invalid; expected 1..=5",
        },
        InvalidMemoryGraphTestCase {
            description: "node upper hard bound is enforced natively",
            pattern: ALPHA,
            depth: 2,
            max_nodes: 201,
            max_edges: 100,
            include_archived: false,
            expected_error_fragment: "max nodes 201 is invalid; expected 1..=200",
        },
        InvalidMemoryGraphTestCase {
            description: "edge upper hard bound is enforced natively",
            pattern: ALPHA,
            depth: 2,
            max_nodes: 50,
            max_edges: 501,
            include_archived: false,
            expected_error_fragment: "max edges 501 is invalid; expected 1..=500",
        },
    ];
    let root = helpers::write_repository(FILES);
    let database_path = root.join("memory.sqlite3");
    rebuild_memory_index(&root, &database_path).expect("graph fixture publishes");
    for test_case in &test_cases {
        let error = query_memory_graph(
            &database_path,
            &MemoryGraphQuery {
                pattern: test_case.pattern.to_owned(),
                direction: MemoryGraphDirection::Outbound,
                relationships: Vec::new(),
                depth: test_case.depth,
                max_nodes: test_case.max_nodes,
                max_edges: test_case.max_edges,
                include_archived: test_case.include_archived,
            },
        )
        .expect_err(test_case.description);
        assert!(
            error
                .to_string()
                .contains(test_case.expected_error_fragment),
            "{}: {error}",
            test_case.description
        );
    }
    fs::remove_dir_all(root).expect("graph fixture is removable");
}
