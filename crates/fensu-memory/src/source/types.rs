//! Closed classifications used by canonical source discovery.

/// Canonical memory artifact ownership.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum ArtifactKind {
    Task,
    Note,
    Decision,
    Skill,
}

/// Intended outcome encoded by a task filename.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum TaskCategory {
    Spike,
    Fix,
    Performance,
    Feature,
    Refactor,
    Chore,
}

/// Task lifecycle encoded exclusively by its directory.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum TaskLifecycle {
    NotStarted,
    InProgress,
    Completed,
    Cancelled,
    Superseded,
}

/// Physical active or archive ownership.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum ArchiveState {
    Active,
    Archived,
}

/// Git visibility states planned for source publication.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum GitTracking {
    Tracked,
    IgnoredRepository,
    IgnoredLocal,
    IgnoredGlobal,
    Untracked,
    Unavailable,
}

/// Stable source-discovery diagnostic classification.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum DiagnosticKind {
    RootMarkdown,
    UnknownStructuralEntry,
    InvalidPathEncoding,
    InvalidDocumentName,
    InvalidTimestamp,
    InvalidArtifactPrefix,
    InvalidTaskCategory,
    InvalidSlug,
    InvalidPlatformName,
    SymlinkRejected,
    UnsupportedFileType,
    MissingSkillDocument,
    Io,
    DuplicateIdentity,
    DuplicateBasename,
    CaseFoldCollision,
}
