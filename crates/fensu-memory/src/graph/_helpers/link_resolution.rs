//! Link-by-link document and heading resolution assembly.

use crate::corpus::models::{CorpusDocument, MemoryCorpus};
use crate::graph::_helpers::{document_targets, heading_targets};
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

struct ResolvedLinkRequest<'a> {
    source: &'a CorpusDocument,
    link: &'a MarkdownLink,
    status: ResolutionStatus,
    target_document_identity: Option<DocumentIdentity>,
    target_section_ordinal: Option<usize>,
}

struct HeadingDiagnosticRequest<'a> {
    source: &'a CorpusDocument,
    link: &'a MarkdownLink,
    target: &'a CorpusDocument,
    kind: GraphDiagnosticKind,
    sections: Vec<Option<usize>>,
}

pub(crate) fn resolve(corpus: &MemoryCorpus) -> LinkResolution {
    let mut links: Vec<ResolvedLink> = Vec::new();
    let mut diagnostics: Vec<GraphDiagnostic> = Vec::new();
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
            resolved_link(ResolvedLinkRequest {
                source,
                link,
                status: ResolutionStatus::External,
                target_document_identity: None,
                target_section_ordinal: None,
            }),
            None,
        );
    }
    let candidates = if link.target.is_empty() && link.heading_fragment.is_some() {
        document_targets::source_candidate(source)
    } else {
        document_targets::resolve(corpus, source, &link.target)
    };
    if candidates.rejected_traversal || candidates.documents.is_empty() {
        let resolved = resolved_link(ResolvedLinkRequest {
            source,
            link,
            status: ResolutionStatus::Unresolved,
            target_document_identity: None,
            target_section_ordinal: None,
        });
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
        let resolved = resolved_link(ResolvedLinkRequest {
            source,
            link,
            status: ResolutionStatus::Ambiguous,
            target_document_identity: None,
            target_section_ordinal: None,
        });
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
            resolved_link(ResolvedLinkRequest {
                source,
                link,
                status: ResolutionStatus::Resolved,
                target_document_identity: target_identity,
                target_section_ordinal: None,
            }),
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
        let resolved = resolved_link(ResolvedLinkRequest {
            source,
            link,
            status: ResolutionStatus::Unresolved,
            target_document_identity: target_identity,
            target_section_ordinal: None,
        });
        let diagnostic = heading_diagnostic(HeadingDiagnosticRequest {
            source,
            link,
            target,
            kind: GraphDiagnosticKind::UnresolvedHeadingTarget,
            sections: Vec::new(),
        });
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
        let resolved = resolved_link(ResolvedLinkRequest {
            source,
            link,
            status: ResolutionStatus::Ambiguous,
            target_document_identity: target_identity,
            target_section_ordinal: None,
        });
        let diagnostic = heading_diagnostic(HeadingDiagnosticRequest {
            source,
            link,
            target,
            kind: GraphDiagnosticKind::AmbiguousHeadingTarget,
            sections: section_ordinals,
        });
        return (resolved, Some(diagnostic));
    }
    (
        resolved_link(ResolvedLinkRequest {
            source,
            link,
            status: ResolutionStatus::Resolved,
            target_document_identity: target_identity,
            target_section_ordinal: section_ordinals[0],
        }),
        None,
    )
}

fn resolved_link(request: ResolvedLinkRequest<'_>) -> ResolvedLink {
    let ResolvedLinkRequest {
        source,
        link,
        status,
        target_document_identity,
        target_section_ordinal,
    } = request;
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

fn heading_diagnostic(request: HeadingDiagnosticRequest<'_>) -> GraphDiagnostic {
    let HeadingDiagnosticRequest {
        source,
        link,
        target,
        kind,
        sections,
    } = request;
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
