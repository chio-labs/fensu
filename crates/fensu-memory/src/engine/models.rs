//! Public results returned by memory engine operations.

/// Counts for one complete memory index publication.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct IndexSummary {
    pub document_count: usize,
    pub section_count: usize,
    pub list_item_count: usize,
    pub list_item_batch_count: usize,
    pub max_loaded_document_batch: usize,
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

/// One stable source-truth validation finding.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct MemoryDiagnostic {
    pub code: &'static str,
    pub repository_relative_path: String,
    pub line: Option<usize>,
    pub column: Option<usize>,
    pub message: String,
    pub remediation: &'static str,
}

/// Direct-source validation findings and optional successful publication summary.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct MemoryCheckResult {
    pub diagnostics: Vec<MemoryDiagnostic>,
    pub published: Option<IndexSummary>,
}

/// One canonical source move published by an archive operation.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct MemoryArchiveMove {
    pub source: String,
    pub destination: String,
}

/// Published archive moves and resulting synchronized index state.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct MemoryArchiveResult {
    pub moves: Vec<MemoryArchiveMove>,
    pub sync: Option<SyncSummary>,
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

/// Traversal orientation for one bounded memory graph query.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum MemoryGraphDirection {
    Outbound,
    Inbound,
    Both,
}

/// Relationship vocabulary accepted by memory graph filtering.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum MemoryGraphRelationship {
    Link,
    Related,
    DependsOn,
    Supersedes,
    DiscoveredFrom,
    Implements,
    Documents,
}

impl MemoryGraphRelationship {
    /// Return the stable CLI and storage representation.
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Link => "link",
            Self::Related => "related",
            Self::DependsOn => "depends-on",
            Self::Supersedes => "supersedes",
            Self::DiscoveredFrom => "discovered-from",
            Self::Implements => "implements",
            Self::Documents => "documents",
        }
    }
}

/// Validated bounded graph retrieval request.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct MemoryGraphQuery {
    pub pattern: String,
    pub direction: MemoryGraphDirection,
    pub relationships: Vec<MemoryGraphRelationship>,
    pub depth: usize,
    pub max_nodes: usize,
    pub max_edges: usize,
    pub include_archived: bool,
}

/// One unique document selected by bounded graph traversal.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct MemoryGraphNode {
    pub identity: String,
    pub artifact_kind: String,
    pub archive_state: String,
    pub repository_relative_path: String,
    pub basename: String,
    pub slug: String,
    pub title: Option<String>,
    pub depth: usize,
    pub root: bool,
}

/// One authored relationship or unresolved/external graph leaf.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct MemoryGraphEdge {
    pub source_document_identity: String,
    pub source_link_ordinal: usize,
    pub relationship: String,
    pub authored_target: String,
    pub resolution_status: String,
    pub target_document_identity: Option<String>,
    pub cycle: bool,
}

/// Deterministic roots, nodes, edges, and explicit budget exhaustion state.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct MemoryGraphResult {
    pub selection: String,
    pub roots: Vec<String>,
    pub nodes: Vec<MemoryGraphNode>,
    pub edges: Vec<MemoryGraphEdge>,
    pub node_budget_exhausted: bool,
    pub edge_budget_exhausted: bool,
}
