//! Link-by-link document and heading resolution assembly.

use crate::corpus::models::{CorpusDocument, MemoryCorpus};
use crate::graph::helpers::{document_targets, heading_targets};
use crate::graph::models::{GraphDiagnostic, ResolvedLink};
use crate::graph::types::{GraphDiagnosticKind, ResolutionStatus};
use crate::markdown::models::MarkdownLink;
use crate::markdown::types::LinkSyntaxKind;
use crate::source::models::DocumentIdentity;

const BLOCK_REFERENCE_PREFIX: char = '^';

#[derive(Debug)]
pub(crate) struct LinkResolution {
    pub(crate) links: Vec<ResolvedLink>,
    pub(crate) diagnostics: Vec<GraphDiagnostic>,
}

pub(crate) fn resolve(corpus: &MemoryCorpus) -> LinkResolution {
    let mut links = Vec::new();
    let mut diagnostics = Vec::new();
    for source in &corpus.documents {
        let Some(markdown) = &source.parsed_markdown else {
            continue;
        };
        for link in &markdown.links {
            let (resolved, diagnostic) = resolve_link(corpus, source, link);
            links.push(resolved);
            diagnostics.extend(diagnostic);
        }
    }
    LinkResolution { links, diagnostics }
}

fn resolve_link(
    corpus: &MemoryCorpus,
    source: &CorpusDocument,
    link: &MarkdownLink,
) -> (ResolvedLink, Option<GraphDiagnostic>) {
    if link.syntax_kind == LinkSyntaxKind::ExternalUrl {
        return (
            resolved_link(source, link, ResolutionStatus::External, None, None),
            None,
        );
    }
    let candidates = if link.target.is_empty() && link.heading_fragment.is_some() {
        document_targets::source_candidate(source)
    } else {
        document_targets::resolve(corpus, source, &link.target)
    };
    if candidates.rejected_traversal || candidates.documents.is_empty() {
        let resolved = resolved_link(source, link, ResolutionStatus::Unresolved, None, None);
        let diagnostic = document_diagnostic(
            source,
            link,
            GraphDiagnosticKind::UnresolvedDocumentTarget,
            Vec::new(),
        );
        return (resolved, Some(diagnostic));
    }
    if candidates.documents.len() > 1 {
        let identities = document_targets::identities(&candidates.documents);
        let resolved = resolved_link(source, link, ResolutionStatus::Ambiguous, None, None);
        let diagnostic = document_diagnostic(
            source,
            link,
            GraphDiagnosticKind::AmbiguousDocumentTarget,
            identities,
        );
        return (resolved, Some(diagnostic));
    }
    resolve_heading(source, link, candidates.documents[0])
}

fn resolve_heading(
    source: &CorpusDocument,
    link: &MarkdownLink,
    target: &CorpusDocument,
) -> (ResolvedLink, Option<GraphDiagnostic>) {
    let target_identity = Some(target.source.identity.clone());
    let Some(fragment) = link.heading_fragment.as_deref() else {
        return (
            resolved_link(
                source,
                link,
                ResolutionStatus::Resolved,
                target_identity,
                None,
            ),
            None,
        );
    };
    let headings = target
        .parsed_markdown
        .as_ref()
        .filter(|_| !fragment.starts_with(BLOCK_REFERENCE_PREFIX))
        .map_or_else(Vec::new, |markdown| {
            heading_targets::resolve(markdown, fragment)
        });
    if headings.is_empty() {
        let resolved = resolved_link(
            source,
            link,
            ResolutionStatus::Unresolved,
            target_identity,
            None,
        );
        let diagnostic = heading_diagnostic(
            source,
            link,
            target,
            GraphDiagnosticKind::UnresolvedHeadingTarget,
            Vec::new(),
        );
        return (resolved, Some(diagnostic));
    }
    let markdown = target.parsed_markdown.as_ref();
    let section_ordinals: Vec<Option<usize>> = headings
        .iter()
        .map(|heading| {
            markdown.and_then(|parsed| heading_targets::section_ordinal(parsed, heading))
        })
        .collect();
    if headings.len() > 1 {
        let resolved = resolved_link(
            source,
            link,
            ResolutionStatus::Ambiguous,
            target_identity,
            None,
        );
        let diagnostic = heading_diagnostic(
            source,
            link,
            target,
            GraphDiagnosticKind::AmbiguousHeadingTarget,
            section_ordinals,
        );
        return (resolved, Some(diagnostic));
    }
    (
        resolved_link(
            source,
            link,
            ResolutionStatus::Resolved,
            target_identity,
            section_ordinals[0],
        ),
        None,
    )
}

fn resolved_link(
    source: &CorpusDocument,
    link: &MarkdownLink,
    status: ResolutionStatus,
    target_document_identity: Option<DocumentIdentity>,
    target_section_ordinal: Option<usize>,
) -> ResolvedLink {
    ResolvedLink {
        source_document_identity: source.source.identity.clone(),
        source_link_ordinal: link.ordinal,
        relationship_kind: link.relationship_kind,
        authored_target: link.target.clone(),
        authored_heading_fragment: link.heading_fragment.clone(),
        status,
        target_document_identity,
        target_section_ordinal,
    }
}

fn document_diagnostic(
    source: &CorpusDocument,
    link: &MarkdownLink,
    kind: GraphDiagnosticKind,
    targets: Vec<DocumentIdentity>,
) -> GraphDiagnostic {
    GraphDiagnostic {
        kind,
        source_document_identity: source.source.identity.clone(),
        source_link_ordinal: Some(link.ordinal),
        authored_target: Some(link.target.clone()),
        authored_heading_fragment: link.heading_fragment.clone(),
        target_document_identities: targets,
        target_section_ordinals: Vec::new(),
        message: format!("{kind:?} for authored document target"),
    }
}

fn heading_diagnostic(
    source: &CorpusDocument,
    link: &MarkdownLink,
    target: &CorpusDocument,
    kind: GraphDiagnosticKind,
    sections: Vec<Option<usize>>,
) -> GraphDiagnostic {
    GraphDiagnostic {
        kind,
        source_document_identity: source.source.identity.clone(),
        source_link_ordinal: Some(link.ordinal),
        authored_target: Some(link.target.clone()),
        authored_heading_fragment: link.heading_fragment.clone(),
        target_document_identities: vec![target.source.identity.clone()],
        target_section_ordinals: sections,
        message: format!("{kind:?} for authored heading target"),
    }
}
