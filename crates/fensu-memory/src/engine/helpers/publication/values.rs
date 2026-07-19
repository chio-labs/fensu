//! Stable scalar encodings shared by SQLite publication phases.

use std::path::Path;
use std::time::{SystemTime, UNIX_EPOCH};

use crate::corpus::models::MemoryCorpus;
use crate::graph::types::ResolutionStatus;
use crate::markdown::models::{ParsedMarkdown, SourceRange};
use crate::markdown::types::{
    CheckboxState, LinkSyntaxKind, RelationshipKind, SemanticHeadingKind,
};
use crate::source::types::{ArchiveState, ArtifactKind, GitTracking, TaskCategory, TaskLifecycle};

pub(crate) fn artifact_kind(value: ArtifactKind) -> &'static str {
    match value {
        ArtifactKind::Task => "task",
        ArtifactKind::Note => "note",
        ArtifactKind::Decision => "decision",
        ArtifactKind::Skill => "skill",
    }
}

pub(crate) fn task_category(value: TaskCategory) -> &'static str {
    match value {
        TaskCategory::Spike => "spike",
        TaskCategory::Fix => "fix",
        TaskCategory::Performance => "performance",
        TaskCategory::Feature => "feature",
        TaskCategory::Refactor => "refactor",
        TaskCategory::Chore => "chore",
    }
}

pub(crate) fn lifecycle(value: TaskLifecycle) -> &'static str {
    match value {
        TaskLifecycle::NotStarted => "not-started",
        TaskLifecycle::InProgress => "in-progress",
        TaskLifecycle::Completed => "completed",
        TaskLifecycle::Cancelled => "cancelled",
        TaskLifecycle::Superseded => "superseded",
    }
}

pub(crate) fn archive_state(value: ArchiveState) -> &'static str {
    match value {
        ArchiveState::Active => "active",
        ArchiveState::Archived => "archived",
    }
}

pub(crate) fn git_tracking(value: GitTracking) -> &'static str {
    match value {
        GitTracking::Tracked => "tracked",
        GitTracking::IgnoredRepository => "ignored-repository",
        GitTracking::IgnoredLocal => "ignored-local",
        GitTracking::IgnoredGlobal => "ignored-global",
        GitTracking::Untracked => "untracked",
        GitTracking::Unavailable => "unavailable",
    }
}

pub(crate) fn checkbox_state(value: CheckboxState) -> &'static str {
    match value {
        CheckboxState::Open => "open",
        CheckboxState::Done => "done",
        CheckboxState::Skipped => "skipped",
        CheckboxState::Custom => "custom",
    }
}

pub(crate) fn link_syntax(value: LinkSyntaxKind) -> &'static str {
    match value {
        LinkSyntaxKind::Markdown => "markdown",
        LinkSyntaxKind::ExternalUrl => "external-url",
        LinkSyntaxKind::Wikilink => "wikilink",
        LinkSyntaxKind::Embed => "embed",
    }
}

pub(crate) fn resolution_status(value: ResolutionStatus) -> &'static str {
    match value {
        ResolutionStatus::Resolved => "resolved",
        ResolutionStatus::Unresolved => "unresolved",
        ResolutionStatus::Ambiguous => "ambiguous",
        ResolutionStatus::External => "external",
    }
}

pub(crate) fn relationship_kind(value: RelationshipKind) -> &'static str {
    match value {
        RelationshipKind::Related => "related",
        RelationshipKind::DependsOn => "depends-on",
        RelationshipKind::Supersedes => "supersedes",
        RelationshipKind::DiscoveredFrom => "discovered-from",
        RelationshipKind::Implements => "implements",
        RelationshipKind::Documents => "documents",
    }
}

pub(crate) fn semantic_kind(value: SemanticHeadingKind) -> &'static str {
    match value {
        SemanticHeadingKind::Status => "status",
        SemanticHeadingKind::Context => "context",
        SemanticHeadingKind::Background => "background",
        SemanticHeadingKind::Objective => "objective",
        SemanticHeadingKind::Goal => "goal",
        SemanticHeadingKind::Principles => "principles",
        SemanticHeadingKind::Contract => "contract",
        SemanticHeadingKind::Constraints => "constraints",
        SemanticHeadingKind::Boundaries => "boundaries",
        SemanticHeadingKind::Phase => "phase",
        SemanticHeadingKind::Stage => "stage",
        SemanticHeadingKind::Milestone => "milestone",
        SemanticHeadingKind::Checkpoint => "checkpoint",
        SemanticHeadingKind::Testing => "testing",
        SemanticHeadingKind::Verification => "verification",
        SemanticHeadingKind::Acceptance => "acceptance",
        SemanticHeadingKind::ExitGate => "exit-gate",
        SemanticHeadingKind::Evidence => "evidence",
        SemanticHeadingKind::Outcome => "outcome",
        SemanticHeadingKind::Risks => "risks",
        SemanticHeadingKind::OpenQuestions => "open-questions",
        SemanticHeadingKind::Deferred => "deferred",
        SemanticHeadingKind::NonGoals => "non-goals",
        SemanticHeadingKind::Relationships => "relationships",
        SemanticHeadingKind::Supersession => "supersession",
    }
}

pub(crate) fn unix_nanoseconds(value: SystemTime) -> i64 {
    match value.duration_since(UNIX_EPOCH) {
        Ok(duration) => i64::try_from(duration.as_nanos()).unwrap_or(i64::MAX),
        Err(error) => -i64::try_from(error.duration().as_nanos()).unwrap_or(i64::MAX),
    }
}

pub(crate) fn filesystem_path(value: &Path) -> String {
    value.to_string_lossy().into_owned()
}

pub(crate) fn heading_path(values: &[String]) -> String {
    values.join(" > ")
}

pub(crate) fn document_diagnostic_count(corpus: &MemoryCorpus, path: &str) -> usize {
    corpus
        .diagnostics
        .iter()
        .filter(|diagnostic| diagnostic.repository_relative_path == path)
        .count()
}

pub(crate) fn preamble_range(parsed: &ParsedMarkdown) -> Option<SourceRange> {
    if parsed.preamble_plain_text.trim().is_empty() {
        return None;
    }
    let (start_byte, end_byte) = preamble_byte_range(parsed);
    Some(source_range(&parsed.raw_markdown, start_byte, end_byte))
}

pub(crate) fn section_ordinal(parsed: &ParsedMarkdown, offset: usize) -> Option<usize> {
    parsed
        .sections
        .iter()
        .find(|section| {
            section.source_range.start_byte <= offset && offset < section.source_range.end_byte
        })
        .map(|section| section.ordinal)
        .or_else(|| {
            let (start_byte, end_byte) = preamble_byte_range(parsed);
            (start_byte <= offset && offset < end_byte).then_some(0)
        })
}

fn preamble_byte_range(parsed: &ParsedMarkdown) -> (usize, usize) {
    let start_byte = parsed
        .headings
        .iter()
        .find(|heading| heading.level == 1)
        .map_or(0, |heading| heading.source_range.end_byte);
    let end_byte = parsed
        .headings
        .iter()
        .find(|heading| heading.source_range.start_byte >= start_byte && heading.level > 1)
        .map_or(parsed.raw_markdown.len(), |heading| {
            heading.source_range.start_byte
        });
    (start_byte, end_byte)
}

fn source_range(source: &str, start_byte: usize, end_byte: usize) -> SourceRange {
    let start_line = line_number(source, start_byte);
    let end_line = if end_byte == start_byte {
        start_line
    } else {
        line_number(source, end_byte.saturating_sub(1)) + 1
    };
    SourceRange {
        start_byte,
        end_byte,
        start_line,
        end_line,
    }
}

fn line_number(source: &str, offset: usize) -> usize {
    source
        .as_bytes()
        .iter()
        .take(offset.min(source.len()))
        .filter(|byte| **byte == b'\n')
        .count()
        + 1
}
