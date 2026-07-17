//! Frozen document-target precedence and relative POSIX path normalization.

use crate::corpus::models::{CorpusDocument, MemoryCorpus};
use crate::source::models::DocumentIdentity;

#[derive(Debug)]
pub(crate) struct DocumentCandidates<'corpus> {
    pub(crate) documents: Vec<&'corpus CorpusDocument>,
    pub(crate) rejected_traversal: bool,
}

pub(crate) fn resolve<'corpus>(
    corpus: &'corpus MemoryCorpus,
    source: &CorpusDocument,
    target: &str,
) -> DocumentCandidates<'corpus> {
    let by_identity = candidates(corpus, |document| document.source.identity.0 == target);
    if !by_identity.is_empty() {
        return matched(by_identity);
    }
    let by_path = candidates(corpus, |document| {
        document.source.canonical_path.repository_relative == target
    });
    if !by_path.is_empty() {
        return matched(by_path);
    }
    let relative_path =
        normalized_relative_path(&source.source.canonical_path.repository_relative, target);
    let Some(relative_path) = relative_path else {
        return DocumentCandidates {
            documents: Vec::new(),
            rejected_traversal: true,
        };
    };
    let by_relative_path = candidates(corpus, |document| {
        document.source.canonical_path.repository_relative == relative_path
    });
    if !by_relative_path.is_empty() {
        return matched(by_relative_path);
    }
    let by_basename = candidates(corpus, |document| document.source.basename == target);
    if !by_basename.is_empty() {
        return matched(by_basename);
    }
    let by_stem = candidates(corpus, |document| {
        filename_stem(&document.source.basename) == target
    });
    if !by_stem.is_empty() {
        return matched(by_stem);
    }
    matched(candidates(corpus, |document| {
        document.source.slug == target
    }))
}

pub(crate) fn source_candidate(source: &CorpusDocument) -> DocumentCandidates<'_> {
    matched(vec![source])
}

fn candidates<F>(corpus: &MemoryCorpus, predicate: F) -> Vec<&CorpusDocument>
where
    F: Fn(&CorpusDocument) -> bool,
{
    corpus
        .documents
        .iter()
        .filter(|document| predicate(document))
        .collect()
}

fn matched(documents: Vec<&CorpusDocument>) -> DocumentCandidates<'_> {
    DocumentCandidates {
        documents,
        rejected_traversal: false,
    }
}

fn filename_stem(basename: &str) -> &str {
    basename.strip_suffix(".md").unwrap_or(basename)
}

fn normalized_relative_path(source_path: &str, target: &str) -> Option<String> {
    if target.starts_with('/') {
        return None;
    }
    let source_directory = source_path
        .rsplit_once('/')
        .map_or("", |(directory, _)| directory);
    let mut components: Vec<&str> = source_directory.split('/').collect();
    for component in target.split('/') {
        match component {
            "" | "." => {}
            ".." => {
                let _ = components.pop()?;
            }
            value => components.push(value),
        }
    }
    Some(components.join("/"))
}

pub(crate) fn identities(documents: &[&CorpusDocument]) -> Vec<DocumentIdentity> {
    documents
        .iter()
        .map(|document| document.source.identity.clone())
        .collect()
}
