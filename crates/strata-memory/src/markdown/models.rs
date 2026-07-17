//! Immutable owned values emitted by Markdown extraction.

use crate::markdown::types::{
    CheckboxState, CodeBlockKind, LinkSyntaxKind, ListKind, RelationshipKind, SemanticHeadingKind,
};

/// Stable half-open byte and one-based line range in the original source.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct SourceRange {
    pub start_byte: usize,
    pub end_byte: usize,
    pub start_line: usize,
    pub end_line: usize,
}

/// One authored heading with optional semantic metadata.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct MarkdownHeading {
    pub level: u8,
    pub text: String,
    pub ordinal: usize,
    pub slug: String,
    pub heading_path: Vec<String>,
    pub raw_source: String,
    pub source_range: SourceRange,
    pub semantic_kind: Option<SemanticHeadingKind>,
    pub phase_identifier: Option<String>,
    pub phase_title: Option<String>,
}

/// One linear authored section beginning at a non-title heading.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct MarkdownSection {
    pub ordinal: usize,
    pub heading_ordinal: usize,
    pub heading_path: Vec<String>,
    pub raw_markdown: String,
    pub plain_text: String,
    pub source_range: SourceRange,
}

/// Raw and normalized checkbox state attached to a list item.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct MarkdownCheckbox {
    pub raw_marker: String,
    pub state: CheckboxState,
}

/// One ordered or unordered list item, including nested ownership.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct MarkdownListItem {
    pub ordinal: usize,
    pub kind: ListKind,
    pub ordered_number: Option<u64>,
    pub nesting_depth: usize,
    pub parent_ordinal: Option<usize>,
    pub raw_markdown: String,
    pub plain_text: String,
    pub source_line: usize,
    pub source_range: SourceRange,
    pub section_ordinal: Option<usize>,
    pub heading_path: Vec<String>,
    pub checkbox: Option<MarkdownCheckbox>,
    pub leading_key: Option<String>,
    pub relationship_kind: Option<RelationshipKind>,
}

/// One fenced or indented code block.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct MarkdownCodeBlock {
    pub ordinal: usize,
    pub kind: CodeBlockKind,
    pub info: Option<String>,
    pub language: Option<String>,
    pub raw_content: String,
    pub raw_markdown: String,
    pub source_line: usize,
    pub source_range: SourceRange,
}

/// One ordinary, external, wiki, or embedded link occurrence.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct MarkdownLink {
    pub ordinal: usize,
    pub syntax_kind: LinkSyntaxKind,
    pub target: String,
    pub alias: Option<String>,
    pub display: Option<String>,
    pub heading_fragment: Option<String>,
    pub raw_source: String,
    pub source_line: usize,
    pub source_range: SourceRange,
    pub list_item_ordinal: Option<usize>,
    pub relationship_kind: Option<RelationshipKind>,
}

/// One Obsidian inline tag outside excluded syntax.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct MarkdownTag {
    pub ordinal: usize,
    pub name: String,
    pub raw_source: String,
    pub source_line: usize,
    pub source_range: SourceRange,
}

/// Complete generic extraction result for one UTF-8 Markdown source.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct ParsedMarkdown {
    pub raw_markdown: String,
    pub plain_text: String,
    pub title: Option<String>,
    pub preamble_raw_markdown: String,
    pub preamble_plain_text: String,
    pub headings: Vec<MarkdownHeading>,
    pub sections: Vec<MarkdownSection>,
    pub list_items: Vec<MarkdownListItem>,
    pub code_blocks: Vec<MarkdownCodeBlock>,
    pub links: Vec<MarkdownLink>,
    pub tags: Vec<MarkdownTag>,
}
