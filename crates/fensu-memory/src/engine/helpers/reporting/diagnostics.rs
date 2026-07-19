//! Stable public diagnostics derived from source, corpus, and graph findings.

use std::collections::BTreeMap;

use crate::corpus::models::{CorpusDiagnostic, MemoryCorpus};
use crate::corpus::types::CorpusDiagnosticKind;
use crate::engine::models::MemoryDiagnostic;
use crate::graph::models::{GraphDiagnostic, MemoryGraph};
use crate::graph::types::GraphDiagnosticKind;
use crate::source::models::{DiscoveryDiagnostic, DocumentIdentity};
use crate::source::types::DiagnosticKind;

pub(crate) fn collect(corpus: &MemoryCorpus, graph: &MemoryGraph) -> Vec<MemoryDiagnostic> {
    let mut diagnostics: Vec<MemoryDiagnostic> = corpus
        .source_diagnostics
        .iter()
        .map(source_diagnostic)
        .chain(corpus.diagnostics.iter().map(corpus_diagnostic))
        .collect();
    let locations = document_locations(corpus);
    diagnostics.extend(
        graph
            .diagnostics
            .iter()
            .map(|diagnostic| graph_diagnostic(diagnostic, &locations)),
    );
    diagnostics.sort_by(|left, right| {
        (
            &left.repository_relative_path,
            left.line,
            left.column,
            left.code,
            &left.message,
        )
            .cmp(&(
                &right.repository_relative_path,
                right.line,
                right.column,
                right.code,
                &right.message,
            ))
    });
    diagnostics
}

fn source_diagnostic(diagnostic: &DiscoveryDiagnostic) -> MemoryDiagnostic {
    let (code, remediation) = source_classification(diagnostic.kind);
    MemoryDiagnostic {
        code,
        repository_relative_path: diagnostic.repository_relative_path.clone(),
        line: None,
        column: None,
        message: diagnostic.message.clone(),
        remediation,
    }
}

fn source_classification(kind: DiagnosticKind) -> (&'static str, &'static str) {
    match kind {
        DiagnosticKind::InvalidDocumentName
        | DiagnosticKind::InvalidTimestamp
        | DiagnosticKind::InvalidArtifactPrefix
        | DiagnosticKind::InvalidTaskCategory
        | DiagnosticKind::InvalidSlug
        | DiagnosticKind::InvalidPlatformName => (
            "MEM001",
            "Rename the document to the canonical timestamp, artifact prefix, and kebab-case grammar.",
        ),
        DiagnosticKind::RootMarkdown
        | DiagnosticKind::UnknownStructuralEntry
        | DiagnosticKind::MissingSkillDocument => (
            "MEM002",
            "Move the source into its canonical task, knowledge, skill, or archive location.",
        ),
        DiagnosticKind::InvalidPathEncoding
        | DiagnosticKind::SymlinkRejected
        | DiagnosticKind::UnsupportedFileType => (
            "MEM007",
            "Use a regular file beneath the canonical memory root without symlinks or unsafe path components.",
        ),
        DiagnosticKind::Io => (
            "MEM008",
            "Restore readable filesystem access and rerun memory validation.",
        ),
        DiagnosticKind::DuplicateIdentity
        | DiagnosticKind::DuplicateBasename
        | DiagnosticKind::CaseFoldCollision => (
            "MEM009",
            "Rename one conflicting source so identities and portable names are unique.",
        ),
    }
}

fn corpus_diagnostic(diagnostic: &CorpusDiagnostic) -> MemoryDiagnostic {
    let remediation = match diagnostic.kind {
        CorpusDiagnosticKind::ReadFailure => {
            "Restore readable filesystem access and rerun memory validation."
        }
        CorpusDiagnosticKind::ContentChangedDuringLoad => {
            "Stop concurrent source modification and rerun memory validation."
        }
        CorpusDiagnosticKind::InvalidUtf8 => "Encode the memory document as valid UTF-8.",
        CorpusDiagnosticKind::MissingOrEmptyTitle | CorpusDiagnosticKind::FirstHeadingNotH1 => {
            "Start the document with one non-empty level-one Markdown title."
        }
        CorpusDiagnosticKind::MultipleH1Titles => {
            "Keep one level-one title and convert later headings to subordinate levels."
        }
    };
    MemoryDiagnostic {
        code: "MEM003",
        repository_relative_path: diagnostic.repository_relative_path.clone(),
        line: Some(1),
        column: Some(0),
        message: diagnostic.message.clone(),
        remediation,
    }
}

fn graph_diagnostic(
    diagnostic: &GraphDiagnostic,
    locations: &BTreeMap<DocumentIdentity, (&str, BTreeMap<usize, usize>)>,
) -> MemoryDiagnostic {
    let (code, remediation) = match diagnostic.kind {
        GraphDiagnosticKind::UnresolvedDocumentTarget
        | GraphDiagnosticKind::UnresolvedHeadingTarget => (
            "MEM004",
            "Correct the authored target or add the missing canonical document or heading.",
        ),
        GraphDiagnosticKind::AmbiguousDocumentTarget
        | GraphDiagnosticKind::AmbiguousHeadingTarget => (
            "MEM005",
            "Use an exact canonical path or identity that resolves to one target.",
        ),
        GraphDiagnosticKind::SelfDependency | GraphDiagnosticKind::DependencyCycle => (
            "MEM006",
            "Remove the self-dependency or revise dependencies so the task graph is acyclic.",
        ),
    };
    let location = locations.get(&diagnostic.source_document_identity);
    let path = location
        .map(|(path, _)| (*path).to_owned())
        .unwrap_or_else(|| diagnostic.source_document_identity.0.clone());
    let line = location.and_then(|(_, links)| {
        diagnostic
            .source_link_ordinal
            .and_then(|ordinal| links.get(&ordinal).copied())
    });
    MemoryDiagnostic {
        code,
        repository_relative_path: path,
        line,
        column: line.map(|_| 0),
        message: diagnostic.message.clone(),
        remediation,
    }
}

fn document_locations(
    corpus: &MemoryCorpus,
) -> BTreeMap<DocumentIdentity, (&str, BTreeMap<usize, usize>)> {
    corpus
        .documents
        .iter()
        .map(|document| {
            let links = document
                .parsed_markdown
                .as_ref()
                .map(|parsed| {
                    parsed
                        .links
                        .iter()
                        .map(|link| (link.ordinal, link.source_line))
                        .collect()
                })
                .unwrap_or_default();
            (
                document.source.identity.clone(),
                (
                    document.source.canonical_path.repository_relative.as_str(),
                    links,
                ),
            )
        })
        .collect()
}
