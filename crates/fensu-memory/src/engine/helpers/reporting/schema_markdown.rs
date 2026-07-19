//! Frozen columns for list, link, and tag relations.

use crate::engine::models::MemorySchemaColumn;

macro_rules! c {
    ($name:literal, $data_type:literal, $nullable:literal, $comment:literal) => {
        MemorySchemaColumn {
            name: $name,
            data_type: $data_type,
            nullable: $nullable,
            comment: $comment,
        }
    };
}

pub(super) const LIST_ITEM_COLUMNS: &[MemorySchemaColumn] = &[
    c!(
        "document_identity",
        "VARCHAR",
        false,
        "Owning document identity."
    ),
    c!(
        "ordinal",
        "UBIGINT",
        false,
        "Stable item ordinal within the document."
    ),
    c!(
        "section_ordinal",
        "UBIGINT",
        true,
        "Owning section ordinal."
    ),
    c!(
        "parent_ordinal",
        "UBIGINT",
        true,
        "Parent list-item ordinal."
    ),
    c!("kind", "VARCHAR", false, "Ordered or unordered list kind."),
    c!(
        "nesting_depth",
        "UBIGINT",
        false,
        "Zero-based list nesting depth."
    ),
    c!(
        "ordered_number",
        "UBIGINT",
        true,
        "Authored ordered-list number."
    ),
    c!(
        "heading_path",
        "VARCHAR",
        false,
        "Ordered heading ancestry."
    ),
    c!("raw_markdown", "VARCHAR", false, "Exact item Markdown."),
    c!("plain_text", "VARCHAR", false, "Normalized item text."),
    c!("source_line", "UBIGINT", false, "One-based source line."),
    c!(
        "start_byte",
        "UBIGINT",
        false,
        "Inclusive source byte offset."
    ),
    c!(
        "end_byte",
        "UBIGINT",
        false,
        "Exclusive source byte offset."
    ),
    c!(
        "start_line",
        "UBIGINT",
        false,
        "One-based source start line."
    ),
    c!("end_line", "UBIGINT", false, "One-based source end line."),
    c!("checkbox_raw", "VARCHAR", true, "Authored checkbox marker."),
    c!(
        "checkbox_state",
        "VARCHAR",
        true,
        "Normalized checkbox state."
    ),
    c!(
        "leading_key",
        "VARCHAR",
        true,
        "Normalized leading list key."
    ),
    c!(
        "relationship_kind",
        "VARCHAR",
        true,
        "Recognized relationship kind."
    ),
];

pub(super) const LINK_COLUMNS: &[MemorySchemaColumn] = &[
    c!(
        "document_identity",
        "VARCHAR",
        false,
        "Owning document identity."
    ),
    c!(
        "ordinal",
        "UBIGINT",
        false,
        "Stable link ordinal within the document."
    ),
    c!(
        "section_ordinal",
        "UBIGINT",
        true,
        "Owning section ordinal."
    ),
    c!(
        "list_item_ordinal",
        "UBIGINT",
        true,
        "Owning list-item ordinal."
    ),
    c!(
        "syntax_kind",
        "VARCHAR",
        false,
        "Markdown, URL, wikilink, or embed syntax."
    ),
    c!("target", "VARCHAR", false, "Authored link target."),
    c!("alias", "VARCHAR", true, "Authored wikilink alias."),
    c!("display_text", "VARCHAR", true, "Authored display text."),
    c!(
        "heading_fragment",
        "VARCHAR",
        true,
        "Authored target heading fragment."
    ),
    c!(
        "resolved_document_identity",
        "VARCHAR",
        true,
        "Resolved target document identity."
    ),
    c!(
        "resolved_section_ordinal",
        "UBIGINT",
        true,
        "Resolved target section ordinal."
    ),
    c!(
        "resolution_status",
        "VARCHAR",
        false,
        "Resolved, unresolved, ambiguous, or external."
    ),
    c!(
        "relationship_kind",
        "VARCHAR",
        true,
        "Recognized relationship kind."
    ),
    c!(
        "explicit",
        "BOOLEAN",
        false,
        "Whether the edge was explicitly authored."
    ),
    c!(
        "raw_source",
        "VARCHAR",
        false,
        "Exact authored link source."
    ),
    c!("source_line", "UBIGINT", false, "One-based source line."),
    c!(
        "start_byte",
        "UBIGINT",
        false,
        "Inclusive source byte offset."
    ),
    c!(
        "end_byte",
        "UBIGINT",
        false,
        "Exclusive source byte offset."
    ),
    c!(
        "start_line",
        "UBIGINT",
        false,
        "One-based source start line."
    ),
    c!("end_line", "UBIGINT", false, "One-based source end line."),
];

pub(super) const TAG_COLUMNS: &[MemorySchemaColumn] = &[
    c!(
        "document_identity",
        "VARCHAR",
        false,
        "Owning document identity."
    ),
    c!(
        "ordinal",
        "UBIGINT",
        false,
        "Stable tag ordinal within the document."
    ),
    c!(
        "section_ordinal",
        "UBIGINT",
        true,
        "Owning section ordinal."
    ),
    c!("name", "VARCHAR", false, "Normalized tag name."),
    c!("raw_source", "VARCHAR", false, "Exact authored tag source."),
    c!("source_line", "UBIGINT", false, "One-based source line."),
    c!(
        "start_byte",
        "UBIGINT",
        false,
        "Inclusive source byte offset."
    ),
    c!(
        "end_byte",
        "UBIGINT",
        false,
        "Exclusive source byte offset."
    ),
    c!(
        "start_line",
        "UBIGINT",
        false,
        "One-based source start line."
    ),
    c!("end_line", "UBIGINT", false, "One-based source end line."),
];
