//! Stable vocabularies used by Markdown semantic recognition.

use crate::markdown::types::{RelationshipKind, SemanticHeadingKind};

pub(crate) const FRONTMATTER_DELIMITER: &str = "---";
pub(crate) const MAX_PHASE_IDENTIFIER_LENGTH: usize = 8;

pub(crate) const RELATIONSHIP_KINDS: &[(&str, RelationshipKind)] = &[
    ("related", RelationshipKind::Related),
    ("depends-on", RelationshipKind::DependsOn),
    ("supersedes", RelationshipKind::Supersedes),
    ("discovered-from", RelationshipKind::DiscoveredFrom),
    ("implements", RelationshipKind::Implements),
    ("documents", RelationshipKind::Documents),
];

pub(crate) const SEMANTIC_HEADING_KINDS: &[(&str, SemanticHeadingKind)] = &[
    ("status", SemanticHeadingKind::Status),
    ("context", SemanticHeadingKind::Context),
    ("background", SemanticHeadingKind::Background),
    ("objective", SemanticHeadingKind::Objective),
    ("goal", SemanticHeadingKind::Goal),
    ("principles", SemanticHeadingKind::Principles),
    ("contract", SemanticHeadingKind::Contract),
    ("constraints", SemanticHeadingKind::Constraints),
    ("boundaries", SemanticHeadingKind::Boundaries),
    ("phase", SemanticHeadingKind::Phase),
    ("stage", SemanticHeadingKind::Stage),
    ("milestone", SemanticHeadingKind::Milestone),
    ("checkpoint", SemanticHeadingKind::Checkpoint),
    ("testing", SemanticHeadingKind::Testing),
    ("verification", SemanticHeadingKind::Verification),
    ("acceptance", SemanticHeadingKind::Acceptance),
    ("exit-gate", SemanticHeadingKind::ExitGate),
    ("evidence", SemanticHeadingKind::Evidence),
    ("outcome", SemanticHeadingKind::Outcome),
    ("risks", SemanticHeadingKind::Risks),
    ("open-questions", SemanticHeadingKind::OpenQuestions),
    ("deferred", SemanticHeadingKind::Deferred),
    ("non-goals", SemanticHeadingKind::NonGoals),
    ("relationships", SemanticHeadingKind::Relationships),
    ("supersession", SemanticHeadingKind::Supersession),
];

pub(crate) const SEMANTIC_HEADING_ALIASES: &[(&str, SemanticHeadingKind)] = &[
    ("why-this-document-exists", SemanticHeadingKind::Objective),
    ("goals", SemanticHeadingKind::Goal),
    ("testing-and-verification", SemanticHeadingKind::Testing),
    ("acceptance-criteria", SemanticHeadingKind::Acceptance),
    ("exit-criteria", SemanticHeadingKind::ExitGate),
    ("open-question", SemanticHeadingKind::OpenQuestions),
    ("risk", SemanticHeadingKind::Risks),
    ("non-goal", SemanticHeadingKind::NonGoals),
];
