//! Frozen columns unique to convenience views.

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

pub(super) const TASK_PHASE_COLUMNS: &[MemorySchemaColumn] = &[
    c!(
        "document_identity",
        "VARCHAR",
        false,
        "Owning task identity."
    ),
    c!("document_title", "VARCHAR", true, "Owning task title."),
    c!(
        "section_ordinal",
        "UBIGINT",
        false,
        "Phase section ordinal."
    ),
    c!(
        "semantic_kind",
        "VARCHAR",
        true,
        "Phase-like semantic heading kind."
    ),
    c!("phase_key", "VARCHAR", true, "Recognized phase identifier."),
    c!("phase_title", "VARCHAR", true, "Recognized phase title."),
    c!("heading_text", "VARCHAR", true, "Phase heading text."),
    c!("heading_path", "VARCHAR", true, "Ordered heading ancestry."),
    c!("raw_markdown", "VARCHAR", false, "Exact phase Markdown."),
    c!("plain_text", "VARCHAR", false, "Normalized phase text."),
    c!(
        "start_line",
        "UBIGINT",
        false,
        "One-based source start line."
    ),
    c!("end_line", "UBIGINT", false, "One-based source end line."),
];

pub(super) const CHECKBOX_COLUMNS: &[MemorySchemaColumn] = &[
    c!(
        "artifact_kind",
        "VARCHAR",
        false,
        "Owning document artifact kind."
    ),
    c!(
        "lifecycle",
        "VARCHAR",
        true,
        "Owning task lifecycle when applicable."
    ),
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

pub(super) const RELATIONSHIP_COLUMNS: &[MemorySchemaColumn] = &[
    c!(
        "source_artifact_kind",
        "VARCHAR",
        false,
        "Source document artifact kind."
    ),
    c!("source_title", "VARCHAR", true, "Source document title."),
    c!(
        "document_identity",
        "VARCHAR",
        false,
        "Source document identity."
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
        "Authored link syntax kind."
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
        "Relationship resolution status."
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
        "Whether the relationship was authored."
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

pub(super) const TASK_DEPENDENCY_COLUMNS: &[MemorySchemaColumn] = &[
    c!(
        "source_artifact_kind",
        "VARCHAR",
        false,
        "Source document artifact kind."
    ),
    c!("source_title", "VARCHAR", true, "Source task title."),
    c!(
        "document_identity",
        "VARCHAR",
        false,
        "Source task identity."
    ),
    c!(
        "ordinal",
        "UBIGINT",
        false,
        "Stable link ordinal within the task."
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
        "Authored link syntax kind."
    ),
    c!("target", "VARCHAR", false, "Authored dependency target."),
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
        "Resolved target task identity."
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
        "Dependency target resolution status."
    ),
    c!(
        "relationship_kind",
        "VARCHAR",
        true,
        "Depends-on relationship kind."
    ),
    c!(
        "explicit",
        "BOOLEAN",
        false,
        "Whether the dependency was authored."
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
    c!(
        "target_artifact_kind",
        "VARCHAR",
        true,
        "Resolved target artifact kind."
    ),
    c!(
        "target_lifecycle",
        "VARCHAR",
        true,
        "Resolved target task lifecycle."
    ),
    c!(
        "dependency_state",
        "VARCHAR",
        false,
        "Blocking, satisfied, or unresolved state."
    ),
];
