//! Compiled public relation inventory and focused metadata lookup.

use crate::engine::constants;
use crate::engine::helpers::reporting::{
    schema_core, schema_markdown, schema_skill_view, schema_views,
};
use crate::engine::models::{MemorySchemaOverview, MemorySchemaRelation};

macro_rules! relation {
    ($name:literal, $kind:literal, $comment:literal, $columns:expr) => {
        MemorySchemaRelation {
            name: $name,
            kind: $kind,
            comment: $comment,
            columns: $columns,
        }
    };
}

const RELATIONS: &[MemorySchemaRelation] = &[
    relation!(
        "memory.documents",
        "table",
        "All active and archived canonical documents.",
        schema_core::DOCUMENT_COLUMNS
    ),
    relation!(
        "memory.sections",
        "table",
        "Parsed document preambles and headed sections.",
        schema_core::SECTION_COLUMNS
    ),
    relation!(
        "memory.list_items",
        "table",
        "Normalized Markdown list items.",
        schema_markdown::LIST_ITEM_COLUMNS
    ),
    relation!(
        "memory.links",
        "table",
        "Authored links and deterministic resolution state.",
        schema_markdown::LINK_COLUMNS
    ),
    relation!(
        "memory.tags",
        "table",
        "Normalized authored tags.",
        schema_markdown::TAG_COLUMNS
    ),
    relation!(
        "memory.skill_files",
        "table",
        "Nested canonical skill support files.",
        schema_core::SKILL_FILE_COLUMNS
    ),
    relation!(
        "memory.current_documents",
        "view",
        "Active canonical documents, including invalid documents with nullable parsed content.",
        schema_core::DOCUMENT_COLUMNS
    ),
    relation!(
        "memory.tasks",
        "view",
        "Complete active and archived task history.",
        schema_core::DOCUMENT_COLUMNS
    ),
    relation!(
        "memory.current_tasks",
        "view",
        "Active task documents in every lifecycle.",
        schema_core::DOCUMENT_COLUMNS
    ),
    relation!(
        "memory.archived_tasks",
        "view",
        "Physically archived task documents.",
        schema_core::DOCUMENT_COLUMNS
    ),
    relation!(
        "memory.task_phases",
        "view",
        "Semantically recognized phase-like sections on active tasks.",
        schema_views::TASK_PHASE_COLUMNS
    ),
    relation!(
        "memory.checkboxes",
        "view",
        "Normalized checkbox list items on active documents.",
        schema_views::CHECKBOX_COLUMNS
    ),
    relation!(
        "memory.task_checkboxes",
        "view",
        "Normalized checkbox list items belonging to active tasks.",
        schema_views::CHECKBOX_COLUMNS
    ),
    relation!(
        "memory.relationships",
        "view",
        "Explicit authored relationship links on active documents.",
        schema_views::RELATIONSHIP_COLUMNS
    ),
    relation!(
        "memory.task_dependencies",
        "view",
        "Explicit depends-on relationships authored by active tasks.",
        schema_views::TASK_DEPENDENCY_COLUMNS
    ),
    relation!(
        "memory.blocked_tasks",
        "view",
        "Active tasks with at least one unresolved authored dependency.",
        schema_core::DOCUMENT_COLUMNS
    ),
    relation!(
        "memory.notes",
        "view",
        "Active note documents.",
        schema_core::DOCUMENT_COLUMNS
    ),
    relation!(
        "memory.decisions",
        "view",
        "Active decision documents.",
        schema_core::DOCUMENT_COLUMNS
    ),
    relation!(
        "memory.skills",
        "view",
        "Active skill documents with derived support-file and installation facts.",
        schema_skill_view::SKILL_VIEW_COLUMNS
    ),
    relation!(
        "memory.broken_links",
        "view",
        "Internal links awaiting successful resolution.",
        schema_markdown::LINK_COLUMNS
    ),
];

pub(crate) fn overview() -> MemorySchemaOverview {
    MemorySchemaOverview {
        schema_version: constants::SCHEMA_VERSION,
        parser_contract_version: constants::PARSER_CONTRACT_VERSION,
        relations: RELATIONS.to_vec(),
    }
}

pub(crate) fn find_relation(name: &str) -> Option<MemorySchemaRelation> {
    let qualified = if name.starts_with("memory.") {
        name.to_owned()
    } else {
        format!("memory.{name}")
    };
    RELATIONS
        .iter()
        .copied()
        .find(|item| item.name == qualified)
}

pub(crate) fn relations() -> &'static [MemorySchemaRelation] {
    RELATIONS
}
