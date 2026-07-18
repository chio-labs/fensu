//! Document reading, integrity verification, and title validation.

use std::fs;

use rayon::iter::{IntoParallelIterator, ParallelIterator};
use sha2::{Digest, Sha256};

use crate::corpus::models::{CorpusDiagnostic, CorpusDocument, MemoryCorpus};
use crate::corpus::types::CorpusDiagnosticKind;
use crate::markdown::main::parse_markdown::parse_markdown;
use crate::markdown::models::ParsedMarkdown;
use crate::source::models::{DiscoveredDocument, DiscoveryResult};

pub(crate) fn load(mut discovery: DiscoveryResult) -> MemoryCorpus {
    discovery
        .documents
        .sort_by(|left, right| document_path(left).cmp(document_path(right)));
    discovery.skill_files.sort_by(|left, right| {
        left.canonical_path
            .repository_relative
            .cmp(&right.canonical_path.repository_relative)
    });
    discovery.diagnostics.sort_by(|left, right| {
        (&left.repository_relative_path, left.kind)
            .cmp(&(&right.repository_relative_path, right.kind))
    });
    let loaded_documents: Vec<(CorpusDocument, Vec<CorpusDiagnostic>)> = discovery
        .documents
        .into_par_iter()
        .map(load_document)
        .collect();
    let mut documents = Vec::with_capacity(loaded_documents.len());
    let mut diagnostics = Vec::new();
    for (document, mut document_diagnostics) in loaded_documents {
        documents.push(document);
        diagnostics.append(&mut document_diagnostics);
    }
    diagnostics.sort_by(|left, right| {
        (&left.repository_relative_path, left.kind)
            .cmp(&(&right.repository_relative_path, right.kind))
    });
    MemoryCorpus {
        documents,
        skill_files: discovery.skill_files,
        source_diagnostics: discovery.diagnostics,
        diagnostics,
    }
}

fn load_document(source: DiscoveredDocument) -> (CorpusDocument, Vec<CorpusDiagnostic>) {
    let path = source.canonical_path.filesystem_path.clone();
    let repository_path = source.canonical_path.repository_relative.clone();
    let bytes = match fs::read(path) {
        Ok(bytes) => bytes,
        Err(_) => {
            return failed_document(
                source,
                CorpusDiagnosticKind::ReadFailure,
                "document could not be read after discovery",
            );
        }
    };
    let current_sha256 = hex::encode(Sha256::digest(&bytes));
    if current_sha256 != source.metadata.content_sha256 {
        return failed_document(
            source,
            CorpusDiagnosticKind::ContentChangedDuringLoad,
            "document content changed after discovery",
        );
    }
    let markdown = match String::from_utf8(bytes) {
        Ok(markdown) => markdown,
        Err(_) => {
            return failed_document(
                source,
                CorpusDiagnosticKind::InvalidUtf8,
                "document content is not valid UTF-8",
            );
        }
    };
    let parsed = parse_markdown(&markdown);
    let diagnostics = title_diagnostics(&repository_path, &parsed);
    let parsed_markdown = diagnostics.is_empty().then_some(parsed);
    (
        CorpusDocument {
            source,
            parsed_markdown,
        },
        diagnostics,
    )
}

fn title_diagnostics(path: &str, parsed: &ParsedMarkdown) -> Vec<CorpusDiagnostic> {
    let mut diagnostics = Vec::new();
    if parsed.title.is_none() {
        diagnostics.push(diagnostic(
            path,
            CorpusDiagnosticKind::MissingOrEmptyTitle,
            "document must have one non-empty H1 title",
        ));
    }
    if parsed
        .headings
        .first()
        .is_some_and(|heading| heading.level != 1)
    {
        diagnostics.push(diagnostic(
            path,
            CorpusDiagnosticKind::FirstHeadingNotH1,
            "first authored heading must be H1",
        ));
    }
    if parsed
        .headings
        .iter()
        .filter(|heading| heading.level == 1)
        .count()
        > 1
    {
        diagnostics.push(diagnostic(
            path,
            CorpusDiagnosticKind::MultipleH1Titles,
            "document must not contain multiple H1 titles",
        ));
    }
    diagnostics
}

fn failed_document(
    source: DiscoveredDocument,
    kind: CorpusDiagnosticKind,
    message: &str,
) -> (CorpusDocument, Vec<CorpusDiagnostic>) {
    let path = source.canonical_path.repository_relative.clone();
    (
        CorpusDocument {
            source,
            parsed_markdown: None,
        },
        vec![diagnostic(&path, kind, message)],
    )
}

fn diagnostic(path: &str, kind: CorpusDiagnosticKind, message: &str) -> CorpusDiagnostic {
    CorpusDiagnostic {
        kind,
        repository_relative_path: path.to_owned(),
        message: message.to_owned(),
    }
}

fn document_path(document: &DiscoveredDocument) -> &str {
    &document.canonical_path.repository_relative
}
