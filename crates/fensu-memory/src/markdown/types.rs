//! Closed classifications emitted by Markdown extraction.

/// Markdown list marker family.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum ListKind {
    Ordered,
    Unordered,
}

/// Normalized task checkbox state.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum CheckboxState {
    Open,
    Done,
    Skipped,
    Custom,
}

/// Markdown code block delimiter family.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum CodeBlockKind {
    Fenced,
    Indented,
}

/// Authored link syntax retained for resolution and graph queries.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum LinkSyntaxKind {
    Markdown,
    ExternalUrl,
    Wikilink,
    Embed,
}

/// V1 authored relationship vocabulary.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum RelationshipKind {
    Related,
    DependsOn,
    Supersedes,
    DiscoveredFrom,
    Implements,
    Documents,
}

/// Optional semantic interpretation of an authored heading.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum SemanticHeadingKind {
    Status,
    Context,
    Background,
    Objective,
    Goal,
    Principles,
    Contract,
    Constraints,
    Boundaries,
    Phase,
    Stage,
    Milestone,
    Checkpoint,
    Testing,
    Verification,
    Acceptance,
    ExitGate,
    Evidence,
    Outcome,
    Risks,
    OpenQuestions,
    Deferred,
    NonGoals,
    Relationships,
    Supersession,
}
