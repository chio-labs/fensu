//! Closed classifications emitted by memory graph resolution.

/// Corpus-wide outcome for one authored link.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum ResolutionStatus {
    Resolved,
    Unresolved,
    Ambiguous,
    External,
}

/// Current all-of dependency contribution made by one authored edge.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum DependencyState {
    Satisfied,
    Blocking,
    Unresolved,
}

/// Stable graph diagnostic classification.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum GraphDiagnosticKind {
    UnresolvedDocumentTarget,
    AmbiguousDocumentTarget,
    UnresolvedHeadingTarget,
    AmbiguousHeadingTarget,
    SelfDependency,
    DependencyCycle,
}
