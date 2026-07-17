//! Public results returned by memory engine operations.

/// Counts for one complete memory index publication.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct IndexSummary {
    pub document_count: usize,
    pub section_count: usize,
    pub list_item_count: usize,
    pub link_count: usize,
    pub tag_count: usize,
    pub skill_file_count: usize,
    pub source_diagnostic_count: usize,
    pub corpus_diagnostic_count: usize,
    pub graph_diagnostic_count: usize,
}

/// Live counts derived from the repository corpus and resolved graph.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct MemorySummary {
    pub document_count: usize,
    pub section_count: usize,
    pub list_item_count: usize,
    pub link_count: usize,
    pub tag_count: usize,
    pub skill_file_count: usize,
    pub source_diagnostic_count: usize,
    pub corpus_diagnostic_count: usize,
    pub graph_diagnostic_count: usize,
}

/// Deterministic source reconciliation and resulting index counts.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct SyncSummary {
    pub added_count: usize,
    pub changed_count: usize,
    pub moved_count: usize,
    pub removed_count: usize,
    pub unchanged_count: usize,
    pub rebuilt: bool,
    pub changed: bool,
    pub document_count: usize,
    pub section_count: usize,
    pub link_count: usize,
}

/// Read-only task, knowledge, archive, and index counts.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct MemoryOverview {
    pub not_started_task_count: usize,
    pub in_progress_task_count: usize,
    pub completed_task_count: usize,
    pub cancelled_task_count: usize,
    pub superseded_task_count: usize,
    pub active_note_count: usize,
    pub active_decision_count: usize,
    pub active_skill_count: usize,
    pub archived_task_count: usize,
    pub archived_knowledge_count: usize,
    pub document_count: usize,
    pub section_count: usize,
}

/// One documented column in the compiled memory query schema.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct MemorySchemaColumn {
    pub name: &'static str,
    pub data_type: &'static str,
    pub nullable: bool,
    pub comment: &'static str,
}

/// One public stored table or convenience view in the compiled query schema.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct MemorySchemaRelation {
    pub name: &'static str,
    pub kind: &'static str,
    pub comment: &'static str,
    pub columns: &'static [MemorySchemaColumn],
}

/// Installed schema versions and public relation summaries.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct MemorySchemaOverview {
    pub schema_version: u32,
    pub parser_contract_version: u32,
    pub relations: Vec<MemorySchemaRelation>,
}

/// One JSON- and Python-convertible value returned by a memory query.
#[derive(Clone, Debug, PartialEq)]
pub enum MemoryQueryValue {
    Null,
    Boolean(bool),
    Integer(String),
    Float(f64),
    String(String),
    Array(Vec<MemoryQueryValue>),
    Object(Vec<(String, MemoryQueryValue)>),
}

/// Bounded tabular output from one read-only memory index query.
#[derive(Clone, Debug, PartialEq)]
pub struct MemoryQueryResult {
    pub columns: Vec<String>,
    pub types: Vec<String>,
    pub rows: Vec<Vec<MemoryQueryValue>>,
    pub truncated: bool,
}
