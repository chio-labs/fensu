//! Frozen columns unique to the active skills convenience view.

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

pub(super) const SKILL_VIEW_COLUMNS: &[MemorySchemaColumn] = &[
    c!("identity", "VARCHAR", false, "Stable skill identity."),
    c!("artifact_kind", "VARCHAR", false, "Skill artifact kind."),
    c!("task_category", "VARCHAR", true, "Always null for skills."),
    c!("lifecycle", "VARCHAR", true, "Always null for skills."),
    c!(
        "archive_state",
        "VARCHAR",
        false,
        "Active source ownership."
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
    c!("basename", "VARCHAR", false, "SKILL.md basename."),
    c!("slug", "VARCHAR", false, "Validated skill name."),
    c!(
        "creation_timestamp",
        "VARCHAR",
        true,
        "Always null for skills."
    ),
    c!(
        "content_sha256",
        "VARCHAR",
        false,
        "Complete SKILL.md content hash."
    ),
    c!("byte_size", "UBIGINT", false, "SKILL.md size in bytes."),
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
        "Skill document diagnostic count."
    ),
    c!(
        "raw_markdown",
        "VARCHAR",
        true,
        "Complete SKILL.md source when valid."
    ),
    c!(
        "plain_text",
        "VARCHAR",
        true,
        "Normalized skill text when valid."
    ),
    c!("title", "VARCHAR", true, "Skill title when valid."),
    c!(
        "support_file_count",
        "BIGINT",
        false,
        "Number of nested support files."
    ),
    c!(
        "install_eligible",
        "BOOLEAN",
        false,
        "Whether the complete skill is installable."
    ),
];
