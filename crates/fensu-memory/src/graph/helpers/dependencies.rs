//! Task dependency classification, self-edge checks, and cycle diagnostics.

use std::collections::{BTreeMap, BTreeSet};

use crate::corpus::models::{CorpusDocument, MemoryCorpus};
use crate::graph::helpers::cycles;
use crate::graph::models::{DependencyEdge, GraphDiagnostic, ResolvedLink};
use crate::graph::types::{DependencyState, GraphDiagnosticKind, ResolutionStatus};
use crate::markdown::types::RelationshipKind;
use crate::source::models::DocumentIdentity;
use crate::source::types::{ArtifactKind, TaskLifecycle};

#[derive(Debug)]
pub(crate) struct DependencyGraph {
    pub(crate) edges: Vec<DependencyEdge>,
    pub(crate) diagnostics: Vec<GraphDiagnostic>,
}

pub(crate) fn analyze(corpus: &MemoryCorpus, links: &[ResolvedLink]) -> DependencyGraph {
    let mut edges = Vec::new();
    let mut diagnostics = Vec::new();
    let mut adjacency: BTreeMap<DocumentIdentity, BTreeSet<DocumentIdentity>> = BTreeMap::new();
    for link in links {
        if link.relationship_kind != Some(RelationshipKind::DependsOn) {
            continue;
        }
        let Some(source) = document(corpus, &link.source_document_identity) else {
            continue;
        };
        if source.source.artifact_kind != ArtifactKind::Task {
            continue;
        }
        let target = participating_target(corpus, link);
        edges.push(DependencyEdge {
            source_document_identity: link.source_document_identity.clone(),
            source_link_ordinal: link.source_link_ordinal,
            target_document_identity: link.target_document_identity.clone(),
            state: dependency_state(corpus, link),
        });
        if let Some(target) = target {
            adjacency
                .entry(link.source_document_identity.clone())
                .or_default()
                .insert(target.source.identity.clone());
            adjacency.entry(target.source.identity.clone()).or_default();
            if target.source.identity == link.source_document_identity {
                diagnostics.push(self_diagnostic(link));
            }
        }
    }
    for component in cycles::components(&adjacency) {
        diagnostics.push(cycle_diagnostic(component));
    }
    edges.sort_by_key(|edge| {
        (
            edge.source_document_identity.clone(),
            edge.source_link_ordinal,
        )
    });
    DependencyGraph { edges, diagnostics }
}

fn dependency_state(corpus: &MemoryCorpus, link: &ResolvedLink) -> DependencyState {
    let Some(target) = participating_target(corpus, link) else {
        return DependencyState::Unresolved;
    };
    match target.source.lifecycle {
        Some(TaskLifecycle::Completed) => DependencyState::Satisfied,
        Some(TaskLifecycle::NotStarted | TaskLifecycle::InProgress) => DependencyState::Blocking,
        Some(TaskLifecycle::Cancelled | TaskLifecycle::Superseded) | None => {
            DependencyState::Unresolved
        }
    }
}

fn participating_target<'corpus>(
    corpus: &'corpus MemoryCorpus,
    link: &ResolvedLink,
) -> Option<&'corpus CorpusDocument> {
    if link.status != ResolutionStatus::Resolved {
        return None;
    }
    let identity = link.target_document_identity.as_ref()?;
    document(corpus, identity).filter(|target| target.source.artifact_kind == ArtifactKind::Task)
}

fn document<'corpus>(
    corpus: &'corpus MemoryCorpus,
    identity: &DocumentIdentity,
) -> Option<&'corpus CorpusDocument> {
    corpus
        .documents
        .iter()
        .find(|document| &document.source.identity == identity)
}

fn self_diagnostic(link: &ResolvedLink) -> GraphDiagnostic {
    GraphDiagnostic {
        kind: GraphDiagnosticKind::SelfDependency,
        source_document_identity: link.source_document_identity.clone(),
        source_link_ordinal: Some(link.source_link_ordinal),
        authored_target: Some(link.authored_target.clone()),
        authored_heading_fragment: link.authored_heading_fragment.clone(),
        target_document_identities: vec![link.source_document_identity.clone()],
        target_section_ordinals: Vec::new(),
        message: "task depends on itself".to_owned(),
    }
}

fn cycle_diagnostic(component: Vec<DocumentIdentity>) -> GraphDiagnostic {
    GraphDiagnostic {
        kind: GraphDiagnosticKind::DependencyCycle,
        source_document_identity: component[0].clone(),
        source_link_ordinal: None,
        authored_target: None,
        authored_heading_fragment: None,
        target_document_identities: component,
        target_section_ordinals: Vec::new(),
        message: "resolved task dependencies form a directed cycle".to_owned(),
    }
}
