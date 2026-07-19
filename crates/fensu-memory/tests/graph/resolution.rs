//! Corpus-wide document and heading target resolution behavior.

use crate::helpers;
use crate::test_types::{
    ExpectedGraphDiagnostic, ExpectedResolvedLink, FixtureFile, LinkResolutionTestCase,
};
use fensu_memory::graph::types::{GraphDiagnosticKind, ResolutionStatus};

const SOURCE_DOCUMENT: &str = "# Link Source\n\n[[note:20260717T100001_000000Z]]\n\n[repository path](.ai/knowledge/repo/notes/20260717T100002_000000Z__NOTE-path-target.md)\n\n[relative path](../../knowledge/repo/notes/20260717T100003_000000Z__NOTE-relative-target.md)\n\n[basename](20260717T100004_000000Z__NOTE-basename-target.md)\n\n[[20260717T100005_000000Z__NOTE-stem-target]]\n\n[[slug-target]]\n\n[[#Local Heading]]\n\n[[heading-target#Mixed Heading]]\n\n[[heading-target#mixed-heading]]\n\n[[heading-target#MIXED-HEADING]]\n\n[[heading-target#Heading Target]]\n\n[[archived-target]]\n\n[external](https://example.com/memory)\n\n[[missing-target]]\n\n[[heading-target#Missing Heading]]\n\n[[heading-target#^block-id]]\n\n[[duplicate-heading#Repeat]]\n\n[[SKILL.md]]\n\n[[SKILL]]\n\n[[ambiguous-slug]]\n\n[outside](../../../../escape.md)\n\n## Local Heading\n";

#[test]
fn given_canonical_corpus_when_resolving_links_then_applies_frozen_document_and_heading_precedence()
{
    let test_cases = [LinkResolutionTestCase {
        description: "resolves every precedence tier and reports deterministic target failures",
        files: &[
            FixtureFile {
                path: ".ai/tasks/not-started/20260717T100000_000000Z__FEAT-link-source.md",
                contents: SOURCE_DOCUMENT,
            },
            FixtureFile {
                path: ".ai/knowledge/repo/notes/20260717T100001_000000Z__NOTE-identity-target.md",
                contents: "# Identity Target\n",
            },
            FixtureFile {
                path: ".ai/knowledge/repo/notes/20260717T100002_000000Z__NOTE-path-target.md",
                contents: "# Path Target\n",
            },
            FixtureFile {
                path: ".ai/knowledge/repo/notes/20260717T100003_000000Z__NOTE-relative-target.md",
                contents: "# Relative Target\n",
            },
            FixtureFile {
                path: ".ai/knowledge/repo/notes/20260717T100004_000000Z__NOTE-basename-target.md",
                contents: "# Basename Target\n",
            },
            FixtureFile {
                path: ".ai/knowledge/repo/notes/20260717T100005_000000Z__NOTE-stem-target.md",
                contents: "# Stem Target\n",
            },
            FixtureFile {
                path: ".ai/knowledge/repo/notes/20260717T100006_000000Z__NOTE-slug-target.md",
                contents: "# Slug Target\n",
            },
            FixtureFile {
                path: ".ai/knowledge/repo/notes/20260717T100007_000000Z__NOTE-heading-target.md",
                contents: "# Heading Target\n\n## Mixed Heading\n",
            },
            FixtureFile {
                path: ".ai/_archive/knowledge/repo/notes/20260717T100008_000000Z__NOTE-archived-target.md",
                contents: "# Archived Target\n",
            },
            FixtureFile {
                path: ".ai/knowledge/repo/notes/20260717T100009_000000Z__NOTE-duplicate-heading.md",
                contents: "# Duplicate Heading\n\n## Repeat\n\n## Repeat\n",
            },
            FixtureFile {
                path: ".ai/knowledge/repo/skills/alpha/SKILL.md",
                contents: "# Alpha\n",
            },
            FixtureFile {
                path: ".ai/knowledge/repo/skills/beta/SKILL.md",
                contents: "# Beta\n",
            },
            FixtureFile {
                path: ".ai/knowledge/repo/notes/20260717T100010_000000Z__NOTE-ambiguous-slug.md",
                contents: "# Ambiguous Slug One\n",
            },
            FixtureFile {
                path: ".ai/knowledge/repo/notes/20260717T100011_000000Z__NOTE-ambiguous-slug.md",
                contents: "# Ambiguous Slug Two\n",
            },
        ],
        expected_source_identity: "task:20260717T100000_000000Z",
        expected_block_fragment: "^block-id",
        expected_links: &[
            ExpectedResolvedLink {
                ordinal: 1,
                authored_target: "note:20260717T100001_000000Z",
                expected_status: ResolutionStatus::Resolved,
                expected_target_identity: Some("note:20260717T100001_000000Z"),
                expected_section_ordinal: None,
            },
            ExpectedResolvedLink {
                ordinal: 2,
                authored_target: ".ai/knowledge/repo/notes/20260717T100002_000000Z__NOTE-path-target.md",
                expected_status: ResolutionStatus::Resolved,
                expected_target_identity: Some("note:20260717T100002_000000Z"),
                expected_section_ordinal: None,
            },
            ExpectedResolvedLink {
                ordinal: 3,
                authored_target: "../../knowledge/repo/notes/20260717T100003_000000Z__NOTE-relative-target.md",
                expected_status: ResolutionStatus::Resolved,
                expected_target_identity: Some("note:20260717T100003_000000Z"),
                expected_section_ordinal: None,
            },
            ExpectedResolvedLink {
                ordinal: 4,
                authored_target: "20260717T100004_000000Z__NOTE-basename-target.md",
                expected_status: ResolutionStatus::Resolved,
                expected_target_identity: Some("note:20260717T100004_000000Z"),
                expected_section_ordinal: None,
            },
            ExpectedResolvedLink {
                ordinal: 5,
                authored_target: "20260717T100005_000000Z__NOTE-stem-target",
                expected_status: ResolutionStatus::Resolved,
                expected_target_identity: Some("note:20260717T100005_000000Z"),
                expected_section_ordinal: None,
            },
            ExpectedResolvedLink {
                ordinal: 6,
                authored_target: "slug-target",
                expected_status: ResolutionStatus::Resolved,
                expected_target_identity: Some("note:20260717T100006_000000Z"),
                expected_section_ordinal: None,
            },
            ExpectedResolvedLink {
                ordinal: 7,
                authored_target: "",
                expected_status: ResolutionStatus::Resolved,
                expected_target_identity: Some("task:20260717T100000_000000Z"),
                expected_section_ordinal: Some(1),
            },
            ExpectedResolvedLink {
                ordinal: 8,
                authored_target: "heading-target",
                expected_status: ResolutionStatus::Resolved,
                expected_target_identity: Some("note:20260717T100007_000000Z"),
                expected_section_ordinal: Some(1),
            },
            ExpectedResolvedLink {
                ordinal: 9,
                authored_target: "heading-target",
                expected_status: ResolutionStatus::Resolved,
                expected_target_identity: Some("note:20260717T100007_000000Z"),
                expected_section_ordinal: Some(1),
            },
            ExpectedResolvedLink {
                ordinal: 10,
                authored_target: "heading-target",
                expected_status: ResolutionStatus::Resolved,
                expected_target_identity: Some("note:20260717T100007_000000Z"),
                expected_section_ordinal: Some(1),
            },
            ExpectedResolvedLink {
                ordinal: 11,
                authored_target: "heading-target",
                expected_status: ResolutionStatus::Resolved,
                expected_target_identity: Some("note:20260717T100007_000000Z"),
                expected_section_ordinal: None,
            },
            ExpectedResolvedLink {
                ordinal: 12,
                authored_target: "archived-target",
                expected_status: ResolutionStatus::Resolved,
                expected_target_identity: Some("note:20260717T100008_000000Z"),
                expected_section_ordinal: None,
            },
            ExpectedResolvedLink {
                ordinal: 13,
                authored_target: "https://example.com/memory",
                expected_status: ResolutionStatus::External,
                expected_target_identity: None,
                expected_section_ordinal: None,
            },
            ExpectedResolvedLink {
                ordinal: 14,
                authored_target: "missing-target",
                expected_status: ResolutionStatus::Unresolved,
                expected_target_identity: None,
                expected_section_ordinal: None,
            },
            ExpectedResolvedLink {
                ordinal: 15,
                authored_target: "heading-target",
                expected_status: ResolutionStatus::Unresolved,
                expected_target_identity: Some("note:20260717T100007_000000Z"),
                expected_section_ordinal: None,
            },
            ExpectedResolvedLink {
                ordinal: 16,
                authored_target: "heading-target",
                expected_status: ResolutionStatus::Unresolved,
                expected_target_identity: Some("note:20260717T100007_000000Z"),
                expected_section_ordinal: None,
            },
            ExpectedResolvedLink {
                ordinal: 17,
                authored_target: "duplicate-heading",
                expected_status: ResolutionStatus::Ambiguous,
                expected_target_identity: Some("note:20260717T100009_000000Z"),
                expected_section_ordinal: None,
            },
            ExpectedResolvedLink {
                ordinal: 18,
                authored_target: "SKILL.md",
                expected_status: ResolutionStatus::Ambiguous,
                expected_target_identity: None,
                expected_section_ordinal: None,
            },
            ExpectedResolvedLink {
                ordinal: 19,
                authored_target: "SKILL",
                expected_status: ResolutionStatus::Ambiguous,
                expected_target_identity: None,
                expected_section_ordinal: None,
            },
            ExpectedResolvedLink {
                ordinal: 20,
                authored_target: "ambiguous-slug",
                expected_status: ResolutionStatus::Ambiguous,
                expected_target_identity: None,
                expected_section_ordinal: None,
            },
            ExpectedResolvedLink {
                ordinal: 21,
                authored_target: "../../../../escape.md",
                expected_status: ResolutionStatus::Unresolved,
                expected_target_identity: None,
                expected_section_ordinal: None,
            },
        ],
        expected_diagnostics: &[
            ExpectedGraphDiagnostic {
                source_link_ordinal: Some(14),
                expected_kind: GraphDiagnosticKind::UnresolvedDocumentTarget,
            },
            ExpectedGraphDiagnostic {
                source_link_ordinal: Some(15),
                expected_kind: GraphDiagnosticKind::UnresolvedHeadingTarget,
            },
            ExpectedGraphDiagnostic {
                source_link_ordinal: Some(16),
                expected_kind: GraphDiagnosticKind::UnresolvedHeadingTarget,
            },
            ExpectedGraphDiagnostic {
                source_link_ordinal: Some(17),
                expected_kind: GraphDiagnosticKind::AmbiguousHeadingTarget,
            },
            ExpectedGraphDiagnostic {
                source_link_ordinal: Some(18),
                expected_kind: GraphDiagnosticKind::AmbiguousDocumentTarget,
            },
            ExpectedGraphDiagnostic {
                source_link_ordinal: Some(19),
                expected_kind: GraphDiagnosticKind::AmbiguousDocumentTarget,
            },
            ExpectedGraphDiagnostic {
                source_link_ordinal: Some(20),
                expected_kind: GraphDiagnosticKind::AmbiguousDocumentTarget,
            },
            ExpectedGraphDiagnostic {
                source_link_ordinal: Some(21),
                expected_kind: GraphDiagnosticKind::UnresolvedDocumentTarget,
            },
        ],
    }];

    for test_case in &test_cases {
        let (root, graph) = helpers::load_graph(test_case.files);
        assert_eq!(
            graph.links.len(),
            test_case.expected_links.len(),
            "{}",
            test_case.description
        );
        for (actual, expected) in graph.links.iter().zip(test_case.expected_links) {
            assert_eq!(
                actual.source_document_identity.0, test_case.expected_source_identity,
                "{}",
                test_case.description
            );
            assert_eq!(
                actual.source_link_ordinal, expected.ordinal,
                "{}",
                test_case.description
            );
            assert_eq!(
                actual.authored_target, expected.authored_target,
                "{}",
                test_case.description
            );
            assert_eq!(
                actual.status, expected.expected_status,
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
                actual.target_section_ordinal, expected.expected_section_ordinal,
                "{}",
                test_case.description
            );
        }
        assert_eq!(
            graph.links[15].authored_heading_fragment.as_deref(),
            Some(test_case.expected_block_fragment),
            "{}",
            test_case.description
        );
        let diagnostics: Vec<(Option<usize>, GraphDiagnosticKind)> = graph
            .diagnostics
            .iter()
            .map(|diagnostic| (diagnostic.source_link_ordinal, diagnostic.kind))
            .collect();
        let expected_diagnostics: Vec<(Option<usize>, GraphDiagnosticKind)> = test_case
            .expected_diagnostics
            .iter()
            .map(|diagnostic| (diagnostic.source_link_ordinal, diagnostic.expected_kind))
            .collect();
        assert_eq!(
            diagnostics, expected_diagnostics,
            "{}",
            test_case.description
        );
        helpers::remove_temp_tree(&root);
    }
}
