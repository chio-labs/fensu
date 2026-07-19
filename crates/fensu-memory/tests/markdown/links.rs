//! Markdown links, Obsidian syntax, relationships, tags, and exclusions.

use fensu_memory::markdown::main::parse_markdown::parse_markdown;
use fensu_memory::markdown::types::{LinkSyntaxKind, RelationshipKind};

use crate::test_types::LinkTestCase;

const LINK_DOCUMENT: &str = "# Link Map\n\n## Relationships\n\n- depends-on: [[dependency#Exit Gate|release gate]]\n    - related: [site](https://example.com/path)\n- mystery: ![[diagram#Overview]]\n- documents: [Architecture](../notes/architecture.md#Ownership)\n- supersedes: [[old-plan]]\n- discovered-from: [[origin-task]]\n- implements: [[decision]]\n\nVisit https://bare.example/a. #architecture #architecture/ownership #123 \\#escaped\n\n`[[inline-code]] #inline-code https://inline.invalid`\n\n```text\n[[fenced-code]] #fenced-code https://fenced.invalid\n```\n\n    [[indented-code]] #indented-code https://indented.invalid\n\n%% [[commented]] #commented https://commented.invalid %%\n";

#[test]
fn given_mixed_link_syntax_when_parsing_then_extracts_edges_relationships_and_safe_tags() {
    let test_cases = [LinkTestCase {
        description: "extracts authored links while excluding code and Obsidian comments",
        source: LINK_DOCUMENT,
        expected_syntax_kinds: &[
            LinkSyntaxKind::Wikilink,
            LinkSyntaxKind::ExternalUrl,
            LinkSyntaxKind::Embed,
            LinkSyntaxKind::Markdown,
            LinkSyntaxKind::Wikilink,
            LinkSyntaxKind::Wikilink,
            LinkSyntaxKind::Wikilink,
            LinkSyntaxKind::ExternalUrl,
        ],
        expected_targets: &[
            "dependency",
            "https://example.com/path",
            "diagram",
            "../notes/architecture.md",
            "old-plan",
            "origin-task",
            "decision",
            "https://bare.example/a",
        ],
        expected_aliases: &[
            Some("release gate"),
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        ],
        expected_fragments: &[
            Some("Exit Gate"),
            None,
            Some("Overview"),
            Some("Ownership"),
            None,
            None,
            None,
            None,
        ],
        expected_relationships: &[
            Some(RelationshipKind::DependsOn),
            Some(RelationshipKind::Related),
            None,
            Some(RelationshipKind::Documents),
            Some(RelationshipKind::Supersedes),
            Some(RelationshipKind::DiscoveredFrom),
            Some(RelationshipKind::Implements),
            None,
        ],
        expected_list_item_ordinals: &[
            Some(1),
            Some(2),
            Some(3),
            Some(4),
            Some(5),
            Some(6),
            Some(7),
            None,
        ],
        expected_tags: &["architecture", "architecture/ownership"],
        expected_leading_keys: &[
            Some("depends-on"),
            Some("related"),
            Some("mystery"),
            Some("documents"),
            Some("supersedes"),
            Some("discovered-from"),
            Some("implements"),
        ],
    }];

    for test_case in &test_cases {
        let result = parse_markdown(test_case.source);
        let syntax_kinds: Vec<LinkSyntaxKind> =
            result.links.iter().map(|link| link.syntax_kind).collect();
        let targets: Vec<&str> = result
            .links
            .iter()
            .map(|link| link.target.as_str())
            .collect();
        let aliases: Vec<Option<&str>> = result
            .links
            .iter()
            .map(|link| link.alias.as_deref())
            .collect();
        let fragments: Vec<Option<&str>> = result
            .links
            .iter()
            .map(|link| link.heading_fragment.as_deref())
            .collect();
        let relationships: Vec<Option<RelationshipKind>> = result
            .links
            .iter()
            .map(|link| link.relationship_kind)
            .collect();
        let list_item_ordinals: Vec<Option<usize>> = result
            .links
            .iter()
            .map(|link| link.list_item_ordinal)
            .collect();
        let tags: Vec<&str> = result.tags.iter().map(|tag| tag.name.as_str()).collect();
        let leading_keys: Vec<Option<&str>> = result
            .list_items
            .iter()
            .map(|item| item.leading_key.as_deref())
            .collect();

        assert_eq!(
            syntax_kinds, test_case.expected_syntax_kinds,
            "{}",
            test_case.description
        );
        assert_eq!(
            targets, test_case.expected_targets,
            "{}",
            test_case.description
        );
        assert_eq!(
            aliases, test_case.expected_aliases,
            "{}",
            test_case.description
        );
        assert_eq!(
            fragments, test_case.expected_fragments,
            "{}",
            test_case.description
        );
        assert_eq!(
            relationships, test_case.expected_relationships,
            "{}",
            test_case.description
        );
        assert_eq!(
            list_item_ordinals, test_case.expected_list_item_ordinals,
            "{}",
            test_case.description
        );
        assert_eq!(tags, test_case.expected_tags, "{}", test_case.description);
        assert_eq!(
            leading_keys, test_case.expected_leading_keys,
            "{}",
            test_case.description
        );
    }
}
