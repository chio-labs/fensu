//! Immutable values emitted by canonical source discovery.

use std::path::PathBuf;
use std::time::SystemTime;

use crate::source::types::{
    ArchiveState, ArtifactKind, DiagnosticKind, GitTracking, TaskCategory, TaskLifecycle,
};

/// Native and portable spellings of one canonical source path.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CanonicalPath {
    pub filesystem_path: PathBuf,
    pub repository_relative: String,
    pub archive_state: ArchiveState,
}

/// Stable logical identity derived from a canonical source name.
#[derive(Clone, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub struct DocumentIdentity(pub String);

/// Filesystem and content facts captured from one regular file.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct SourceMetadata {
    pub content_sha256: String,
    pub byte_size: u64,
    pub modified_at: SystemTime,
    pub changed_at: Option<SystemTime>,
}

/// One canonical Markdown document ready for later parsing.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct DiscoveredDocument {
    pub identity: DocumentIdentity,
    pub artifact_kind: ArtifactKind,
    pub task_category: Option<TaskCategory>,
    pub lifecycle: Option<TaskLifecycle>,
    pub canonical_path: CanonicalPath,
    pub basename: String,
    pub slug: String,
    pub creation_timestamp: Option<String>,
    pub metadata: SourceMetadata,
    pub git_tracking: GitTracking,
}

/// One nested regular support file belonging to a skill document.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct DiscoveredSkillFile {
    pub skill_identity: DocumentIdentity,
    pub canonical_path: CanonicalPath,
    pub bundle_relative_path: String,
    pub metadata: SourceMetadata,
    pub git_tracking: GitTracking,
}

/// One recoverable problem found while scanning canonical memory sources.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct DiscoveryDiagnostic {
    pub kind: DiagnosticKind,
    pub repository_relative_path: String,
    pub message: String,
}

/// Complete deterministic source-discovery outcome.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct DiscoveryResult {
    pub documents: Vec<DiscoveredDocument>,
    pub skill_files: Vec<DiscoveredSkillFile>,
    pub diagnostics: Vec<DiscoveryDiagnostic>,
}

/// Validated timestamped document filename parts.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct ParsedDocumentName {
    pub(crate) timestamp: String,
    pub(crate) slug: String,
    pub(crate) category: Option<TaskCategory>,
}
