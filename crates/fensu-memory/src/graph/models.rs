//! Immutable owned values emitted by memory graph resolution.

use crate::graph::types::{DependencyState, GraphDiagnosticKind, ResolutionStatus};
use crate::markdown::types::RelationshipKind;
use crate::source::models::DocumentIdentity;

/// One parsed link annotated with corpus-wide resolution results.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ResolvedLink {
    pub source_document_identity: DocumentIdentity,
    pub source_link_ordinal: usize,
    pub relationship_kind: Option<RelationshipKind>,
    pub authored_target: String,
    pub authored_heading_fragment: Option<String>,
    pub status: ResolutionStatus,
    pub target_document_identity: Option<DocumentIdentity>,
    pub target_section_ordinal: Option<usize>,
}

/// One task-authored dependency and its current satisfaction state.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct DependencyEdge {
    pub source_document_identity: DocumentIdentity,
    pub source_link_ordinal: usize,
    pub target_document_identity: Option<DocumentIdentity>,
    pub state: DependencyState,
}

/// One deterministic graph resolution or dependency problem.
#[derive(Clone, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub struct GraphDiagnostic {
    pub source_document_identity: DocumentIdentity,
    pub source_link_ordinal: Option<usize>,
    pub kind: GraphDiagnosticKind,
    pub authored_target: Option<String>,
    pub authored_heading_fragment: Option<String>,
    pub target_document_identities: Vec<DocumentIdentity>,
    pub target_section_ordinals: Vec<Option<usize>>,
    pub message: String,
}

/// Complete deterministic graph derived from one loaded memory corpus.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct MemoryGraph {
    pub links: Vec<ResolvedLink>,
    pub dependencies: Vec<DependencyEdge>,
    pub diagnostics: Vec<GraphDiagnostic>,
}
