//! Immutable owned values emitted by corpus loading.

use crate::markdown::models::ParsedMarkdown;
use crate::source::models::{DiscoveredDocument, DiscoveredSkillFile, DiscoveryDiagnostic};

use crate::corpus::types::CorpusDiagnosticKind;

/// One discovered document and its validated Markdown representation.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CorpusDocument {
    pub source: DiscoveredDocument,
    pub parsed_markdown: Option<ParsedMarkdown>,
}

/// One recoverable problem found while loading or validating a document.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CorpusDiagnostic {
    pub kind: CorpusDiagnosticKind,
    pub repository_relative_path: String,
    pub message: String,
}

/// Complete deterministic result of discovering and loading memory sources.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct MemoryCorpus {
    pub documents: Vec<CorpusDocument>,
    pub skill_files: Vec<DiscoveredSkillFile>,
    pub source_diagnostics: Vec<DiscoveryDiagnostic>,
    pub diagnostics: Vec<CorpusDiagnostic>,
}
