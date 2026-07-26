//! Nested list and Obsidian checkbox behavior.

use fensu_memory::markdown::main::parse_markdown::parse_markdown;
use fensu_memory::markdown::types::{CheckboxState, ListKind};

use crate::test_types::ListTestCase;

const LIST_DOCUMENT: &str = "# Work\n\n## Checklist\n\n- [ ] root open\n    1. [X] nested done\n    2. [/] nested skipped\n- [?] custom state\n- [ab] malformed marker\n- ordinary item\n";

#[test]
fn given_lists_when_parsing_then_tracks_ownership_order_and_checkbox_states() {
    let test_cases = [
        ListTestCase {
            description:
                "normalizes standard markers and preserves a custom single-character marker",
            source: LIST_DOCUMENT,
            expected_kinds: &[
                ListKind::Unordered,
                ListKind::Ordered,
                ListKind::Ordered,
                ListKind::Unordered,
                ListKind::Unordered,
                ListKind::Unordered,
            ],
            expected_numbers: &[None, Some(1), Some(2), None, None, None],
            expected_depths: &[0, 1, 1, 0, 0, 0],
            expected_parents: &[None, Some(1), Some(1), None, None, None],
            expected_markers: &[Some(" "), Some("X"), Some("/"), Some("?"), None, None],
            expected_states: &[
                Some(CheckboxState::Open),
                Some(CheckboxState::Done),
                Some(CheckboxState::Skipped),
                Some(CheckboxState::Custom),
                None,
                None,
            ],
            expected_plain_texts: &[
                "root open",
                "nested done",
                "nested skipped",
                "custom state",
                "[ab] malformed marker",
                "ordinary item",
            ],
            expected_source_lines: &[5, 6, 7, 8, 9, 10],
            expected_section_ordinals: &[Some(1), Some(1), Some(1), Some(1), Some(1), Some(1)],
        },
        ListTestCase {
            description: "assigns title preamble items to synthetic section zero",
            source: "# Work\n\n- preamble item\n",
            expected_kinds: &[ListKind::Unordered],
            expected_numbers: &[None],
            expected_depths: &[0],
            expected_parents: &[None],
            expected_markers: &[None],
            expected_states: &[None],
            expected_plain_texts: &["preamble item"],
            expected_source_lines: &[3],
            expected_section_ordinals: &[Some(0)],
        },
    ];

    for test_case in &test_cases {
        let result = parse_markdown(test_case.source);
        let kinds: Vec<ListKind> = result.list_items.iter().map(|item| item.kind).collect();
        let numbers: Vec<Option<u64>> = result
            .list_items
            .iter()
            .map(|item| item.ordered_number)
            .collect();
        let depths: Vec<usize> = result
            .list_items
            .iter()
            .map(|item| item.nesting_depth)
            .collect();
        let parents: Vec<Option<usize>> = result
            .list_items
            .iter()
            .map(|item| item.parent_ordinal)
            .collect();
        let markers: Vec<Option<&str>> = result
            .list_items
            .iter()
            .map(|item| {
                item.checkbox
                    .as_ref()
                    .map(|checkbox| checkbox.raw_marker.as_str())
            })
            .collect();
        let states: Vec<Option<CheckboxState>> = result
            .list_items
            .iter()
            .map(|item| item.checkbox.as_ref().map(|checkbox| checkbox.state))
            .collect();
        let plain_texts: Vec<&str> = result
            .list_items
            .iter()
            .map(|item| item.plain_text.as_str())
            .collect();
        let source_lines: Vec<usize> = result
            .list_items
            .iter()
            .map(|item| item.source_line)
            .collect();
        let section_ordinals: Vec<Option<usize>> = result
            .list_items
            .iter()
            .map(|item| item.section_ordinal)
            .collect();

        assert_eq!(kinds, test_case.expected_kinds, "{}", test_case.description);
        assert_eq!(
            numbers, test_case.expected_numbers,
            "{}",
            test_case.description
        );
        assert_eq!(
            depths, test_case.expected_depths,
            "{}",
            test_case.description
        );
        assert_eq!(
            parents, test_case.expected_parents,
            "{}",
            test_case.description
        );
        assert_eq!(
            markers, test_case.expected_markers,
            "{}",
            test_case.description
        );
        assert_eq!(
            states, test_case.expected_states,
            "{}",
            test_case.description
        );
        assert_eq!(
            plain_texts, test_case.expected_plain_texts,
            "{}",
            test_case.description
        );
        assert_eq!(
            source_lines, test_case.expected_source_lines,
            "{}",
            test_case.description
        );
        assert_eq!(
            section_ordinals, test_case.expected_section_ordinals,
            "{}",
            test_case.description
        );
    }
}
