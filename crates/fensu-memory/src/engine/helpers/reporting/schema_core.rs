//! Frozen columns for document, section, and skill-file relations.

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

pub(super) const DOCUMENT_COLUMNS: &[MemorySchemaColumn] = &[
    c!("identity", "VARCHAR", false, "Stable document identity."),
    c!(
        "artifact_kind",
        "VARCHAR",
        false,
        "Task, note, decision, or skill."
    ),
    c!(
        "task_category",
        "VARCHAR",
        true,
        "Filename-derived task category."
    ),
    c!("lifecycle", "VARCHAR", true, "Path-derived task lifecycle."),
    c!(
        "archive_state",
        "VARCHAR",
        false,
        "Active or archived source ownership."
    ),
    c!(
        "repository_relative_path",
        "VARCHAR",
        false,
        "Canonical repository-relative path."
    ),
    c!(
        "filesystem_path",
        "VARCHAR",
        false,
        "Native filesystem path."
    ),
    c!("basename", "VARCHAR", false, "Canonical source basename."),
    c!("slug", "VARCHAR", false, "Validated source slug."),
    c!(
        "creation_timestamp",
        "VARCHAR",
        true,
        "Filename-derived UTC timestamp."
    ),
    c!(
        "content_sha256",
        "VARCHAR",
        false,
        "Complete source content hash."
    ),
    c!("byte_size", "UBIGINT", false, "Source size in bytes."),
    c!(
        "modified_at_ns",
        "HUGEINT",
        false,
        "Filesystem modification time in Unix nanoseconds."
    ),
    c!(
        "changed_at_ns",
        "HUGEINT",
        true,
        "Filesystem change time in Unix nanoseconds when available."
    ),
    c!(
        "git_tracking",
        "VARCHAR",
        false,
        "Pure-Rust Git visibility classification."
    ),
    c!(
        "parse_status",
        "VARCHAR",
        false,
        "Valid or invalid Markdown parse status."
    ),
    c!(
        "diagnostic_count",
        "UBIGINT",
        false,
        "Document corpus diagnostic count."
    ),
    c!(
        "raw_markdown",
        "VARCHAR",
        true,
        "Complete source Markdown when valid."
    ),
    c!(
        "plain_text",
        "VARCHAR",
        true,
        "Normalized document text when valid."
    ),
    c!(
        "title",
        "VARCHAR",
        true,
        "Level-one Markdown title when valid."
    ),
];

pub(super) const SECTION_COLUMNS: &[MemorySchemaColumn] = &[
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
        "Stable section ordinal within the document."
    ),
    c!(
        "heading_ordinal",
        "UBIGINT",
        true,
        "Owning heading ordinal."
    ),
    c!("heading_level", "UTINYINT", true, "Markdown heading level."),
    c!("heading_text", "VARCHAR", true, "Heading text."),
    c!("heading_slug", "VARCHAR", true, "Normalized heading slug."),
    c!("heading_path", "VARCHAR", true, "Ordered heading ancestry."),
    c!(
        "semantic_kind",
        "VARCHAR",
        true,
        "Recognized semantic heading kind."
    ),
    c!("phase_key", "VARCHAR", true, "Recognized phase identifier."),
    c!("phase_title", "VARCHAR", true, "Recognized phase title."),
    c!("raw_markdown", "VARCHAR", false, "Exact section Markdown."),
    c!("plain_text", "VARCHAR", false, "Normalized section text."),
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

pub(super) const SKILL_FILE_COLUMNS: &[MemorySchemaColumn] = &[
    c!(
        "skill_identity",
        "VARCHAR",
        false,
        "Owning skill document identity."
    ),
    c!(
        "repository_relative_path",
        "VARCHAR",
        false,
        "Canonical repository-relative path."
    ),
    c!(
        "filesystem_path",
        "VARCHAR",
        false,
        "Native filesystem path."
    ),
    c!(
        "bundle_relative_path",
        "VARCHAR",
        false,
        "Path relative to the skill bundle root."
    ),
    c!(
        "content_sha256",
        "VARCHAR",
        false,
        "Complete support-file content hash."
    ),
    c!("byte_size", "UBIGINT", false, "Support-file size in bytes."),
    c!(
        "modified_at_ns",
        "HUGEINT",
        false,
        "Filesystem modification time in Unix nanoseconds."
    ),
    c!(
        "changed_at_ns",
        "HUGEINT",
        true,
        "Filesystem change time in Unix nanoseconds when available."
    ),
    c!(
        "git_tracking",
        "VARCHAR",
        false,
        "Pure-Rust Git visibility classification."
    ),
    c!(
        "archived",
        "BOOLEAN",
        false,
        "Whether the owning bundle is archived."
    ),
    c!(
        "install_eligible",
        "BOOLEAN",
        false,
        "Whether this file is eligible for installation."
    ),
];
