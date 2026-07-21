"""Structured models for Fensu Memory operations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class MemoryProject:
    """Resolved project and persistent memory database paths."""

    repository_root: Path
    database_path: Path


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
class MemoryCheckResult:
    """Project paths, direct-source findings, and optional publication counts."""

    project: MemoryProject
    diagnostics: tuple[MemoryDiagnostic, ...]
    published: MemoryIndexSummary | None
