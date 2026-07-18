//! Test-case declarations for generic Markdown extraction.

use strata_memory::markdown::types::{
    CheckboxState, CodeBlockKind, LinkSyntaxKind, ListKind, RelationshipKind, SemanticHeadingKind,
};

pub(crate) struct StructureTestCase {
    pub(crate) description: &'static str,
    pub(crate) source: &'static str,
    pub(crate) expected_title: Option<&'static str>,
    pub(crate) expected_preamble_raw: &'static str,
    pub(crate) expected_preamble_plain: &'static str,
    pub(crate) expected_heading_texts: &'static [&'static str],
    pub(crate) expected_heading_levels: &'static [u8],
    pub(crate) expected_heading_paths: &'static [&'static [&'static str]],
    pub(crate) expected_heading_lines: &'static [(usize, usize)],
    pub(crate) expected_semantic_kinds: &'static [Option<SemanticHeadingKind>],
    pub(crate) expected_phase_identifiers: &'static [Option<&'static str>],
    pub(crate) expected_phase_titles: &'static [Option<&'static str>],
    pub(crate) expected_section_count: usize,
    pub(crate) expected_raw_markdown: &'static str,
}

pub(crate) struct ListTestCase {
    pub(crate) description: &'static str,
    pub(crate) source: &'static str,
    pub(crate) expected_kinds: &'static [ListKind],
    pub(crate) expected_numbers: &'static [Option<u64>],
    pub(crate) expected_depths: &'static [usize],
    pub(crate) expected_parents: &'static [Option<usize>],
    pub(crate) expected_markers: &'static [Option<&'static str>],
    pub(crate) expected_states: &'static [Option<CheckboxState>],
    pub(crate) expected_plain_texts: &'static [&'static str],
    pub(crate) expected_source_lines: &'static [usize],
    pub(crate) expected_section_ordinals: &'static [Option<usize>],
}

pub(crate) struct LinkTestCase {
    pub(crate) description: &'static str,
    pub(crate) source: &'static str,
    pub(crate) expected_syntax_kinds: &'static [LinkSyntaxKind],
    pub(crate) expected_targets: &'static [&'static str],
    pub(crate) expected_aliases: &'static [Option<&'static str>],
    pub(crate) expected_fragments: &'static [Option<&'static str>],
    pub(crate) expected_relationships: &'static [Option<RelationshipKind>],
    pub(crate) expected_list_item_ordinals: &'static [Option<usize>],
    pub(crate) expected_tags: &'static [&'static str],
    pub(crate) expected_leading_keys: &'static [Option<&'static str>],
}

pub(crate) struct CodeBlockTestCase {
    pub(crate) description: &'static str,
    pub(crate) source: &'static str,
    pub(crate) expected_kinds: &'static [CodeBlockKind],
    pub(crate) expected_infos: &'static [Option<&'static str>],
    pub(crate) expected_languages: &'static [Option<&'static str>],
    pub(crate) expected_contents: &'static [&'static str],
    pub(crate) expected_source_lines: &'static [usize],
    pub(crate) expected_plain_text_fragment: &'static str,
}
