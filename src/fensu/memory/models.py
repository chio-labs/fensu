"""Structured models for Fensu Memory operations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fensu.memory.types import MemoryGraphDirection, MemoryGraphRelationship, MemoryQueryValue


@dataclass(frozen=True, slots=True)
class MemoryProject:
    """Resolved project and persistent memory database paths."""

    repository_root: Path
    database_path: Path


@dataclass(frozen=True, slots=True)
class MemorySyncSummary:
    """Source reconciliation counts from one memory sync."""

    added_count: int
    changed_count: int
    moved_count: int
    removed_count: int
    unchanged_count: int
    rebuilt: bool
    changed: bool
    document_count: int
    section_count: int
    link_count: int


@dataclass(frozen=True, slots=True)
class MemoryIndexSummary:
    """Counts from one complete memory index rebuild."""

    document_count: int
    section_count: int
    list_item_count: int
    link_count: int
    tag_count: int
    skill_file_count: int
    source_diagnostic_count: int
    corpus_diagnostic_count: int
    graph_diagnostic_count: int


@dataclass(frozen=True, slots=True)
class MemoryDiagnostic:
    """One stable direct-source memory validation finding."""

    code: str
    repository_relative_path: str
    line: int | None
    column: int | None
    message: str
    remediation: str


@dataclass(frozen=True, slots=True)
class MemoryOverview:
    """Task, knowledge, archive, and index counts."""

    not_started_task_count: int
    in_progress_task_count: int
    completed_task_count: int
    cancelled_task_count: int
    superseded_task_count: int
    active_note_count: int
    active_decision_count: int
    active_skill_count: int
    archived_task_count: int
    archived_knowledge_count: int
    document_count: int
    section_count: int


@dataclass(frozen=True, slots=True)
class MemorySchemaRelation:
    """One public stored table or convenience view."""

    name: str
    kind: str
    comment: str


@dataclass(frozen=True, slots=True)
class MemorySchema:
    """Installed memory schema versions and public relations."""

    schema_version: int
    parser_contract_version: int
    relations: tuple[MemorySchemaRelation, ...]


@dataclass(frozen=True, slots=True)
class MemorySchemaColumn:
    """One documented public relation column."""

    name: str
    data_type: str
    nullable: bool
    comment: str


@dataclass(frozen=True, slots=True)
class MemoryRelationSchema:
    """Focused metadata for one public memory relation."""

    name: str
    kind: str
    comment: str
    columns: tuple[MemorySchemaColumn, ...]


@dataclass(frozen=True, slots=True)
class MemoryQueryResult:
    """Bounded rows and metadata from one read-only memory query."""

    columns: tuple[str, ...]
    types: tuple[str, ...]
    rows: tuple[tuple[MemoryQueryValue, ...], ...]
    truncated: bool


@dataclass(frozen=True, slots=True)
class MemorySyncResult:
    """Project paths and one explicit synchronization result."""

    project: MemoryProject
    sync: MemorySyncSummary


@dataclass(frozen=True, slots=True)
class MemoryOverviewResult:
    """Implicit synchronization and current memory overview."""

    project: MemoryProject
    sync: MemorySyncSummary
    overview: MemoryOverview


@dataclass(frozen=True, slots=True)
class MemoryRebuildResult:
    """Project paths and one complete rebuild result."""

    project: MemoryProject
    summary: MemoryIndexSummary


@dataclass(frozen=True, slots=True)
class MemoryCheckResult:
    """Project paths, direct-source findings, and optional publication counts."""

    project: MemoryProject
    diagnostics: tuple[MemoryDiagnostic, ...]
    published: MemoryIndexSummary | None


@dataclass(frozen=True, slots=True)
class MemoryArchiveMove:
    """One source and destination published by memory archival."""

    source: str
    destination: str


@dataclass(frozen=True, slots=True)
class MemoryArchiveResult:
    """Project paths, published archive moves, and optional synchronization."""

    project: MemoryProject
    moves: tuple[MemoryArchiveMove, ...]
    sync: MemorySyncSummary | None


@dataclass(frozen=True, slots=True)
class MemorySchemaResult:
    """Schema overview or one focused public relation."""

    project: MemoryProject
    schema: MemorySchema | None
    relation: MemoryRelationSchema | None


@dataclass(frozen=True, slots=True)
class MemoryQueryExecution:
    """Implicit synchronization and one read-only query result."""

    project: MemoryProject
    sync: MemorySyncSummary
    query: MemoryQueryResult


@dataclass(frozen=True, slots=True)
class MemoryGraphRequest:
    """Validated graph selector, traversal policy, and hard budgets."""

    pattern: str
    direction: MemoryGraphDirection
    relationships: tuple[MemoryGraphRelationship, ...]
    depth: int
    max_nodes: int
    max_edges: int
    include_archived: bool


@dataclass(frozen=True, slots=True)
class MemoryGraphNode:
    """One unique document selected by graph traversal."""

    identity: str
    artifact_kind: str
    archive_state: str
    repository_relative_path: str
    basename: str
    slug: str
    title: str | None
    depth: int
    root: bool


@dataclass(frozen=True, slots=True)
class MemoryGraphEdge:
    """One resolved edge or unresolved/external graph leaf."""

    source_document_identity: str
    source_link_ordinal: int
    relationship: str
    authored_target: str
    resolution_status: str
    target_document_identity: str | None
    cycle: bool


@dataclass(frozen=True, slots=True)
class MemoryGraphResult:
    """Deterministic graph and explicit budget exhaustion state."""

    selection: str
    roots: tuple[str, ...]
    nodes: tuple[MemoryGraphNode, ...]
    edges: tuple[MemoryGraphEdge, ...]
    node_budget_exhausted: bool
    edge_budget_exhausted: bool


@dataclass(frozen=True, slots=True)
class MemoryGraphExecution:
    """Implicit synchronization and one bounded graph result."""

    project: MemoryProject
    sync: MemorySyncSummary
    request: MemoryGraphRequest
    graph: MemoryGraphResult
