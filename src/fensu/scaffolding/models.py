"""Immutable results produced by repository layout detection."""

from __future__ import annotations

from dataclasses import dataclass

from fensu.scaffolding.types import CandidateProvenance


@dataclass(frozen=True, slots=True)
class PathCandidate:
    """One repository-relative POSIX path and its detection source."""

    path: str
    provenance: CandidateProvenance
    present: bool


@dataclass(frozen=True, slots=True)
class PythonState:
    """Python package and file state outside fixed excluded directories."""

    file_count: int
    package_count: int
    is_empty: bool


@dataclass(frozen=True, slots=True)
class DetectedRepositoryLayout:
    """Ordered runtime, test, and tooling candidates for one repository."""

    roots: tuple[PathCandidate, ...]
    tests: tuple[PathCandidate, ...]
    tooling: tuple[PathCandidate, ...]
    python: PythonState


@dataclass(frozen=True, slots=True)
class InitOptions:
    """Immutable options parsed by the thin CLI adapter."""

    yes: bool = False
    roots: tuple[str, ...] | None = None
    tests: tuple[str, ...] | None = None
    tooling: tuple[str, ...] | None = None
    skills: bool | None = None
    name: str | None = None


@dataclass(frozen=True, slots=True)
class InitPlan:
    """Validated user choices used to render and execute initialization."""

    roots: tuple[str, ...]
    tests: tuple[str, ...]
    tooling: tuple[str, ...]
    project_name: str | None = None


@dataclass(frozen=True, slots=True)
class DriftSummary:
    """Aggregated starting-ruleset faults without full diagnostics."""

    family_counts: tuple[tuple[str, str, int], ...]
    fault_count: int
    file_count: int


@dataclass(frozen=True, slots=True)
class InitExecution:
    """Completed config write and any newly scaffolded paths."""

    config_path: str
    created_paths: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GitIgnorePlan:
    """Captured root gitignore state and the bytes init intends to publish."""

    original: bytes | None
    desired: bytes
    device: int | None
    inode: int | None
