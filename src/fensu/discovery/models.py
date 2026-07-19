"""Discovery models: repository root, scoped files, and discovered trees."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fensu.discovery.types import ScopeName


@dataclass(frozen=True, slots=True)
class RepoRoot:
    """The resolved repository root used for config-relative discovery."""

    path: Path


@dataclass(frozen=True, slots=True)
class ProjectPath:
    """One configured path resolved within the repository."""

    path: Path
    relative_parts: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ProjectSource:
    """One configured Python package root and its import identity."""

    path: Path
    relative_parts: tuple[str, ...]
    import_root: Path
    package_name: str


@dataclass(frozen=True, slots=True)
class ProjectLayout:
    """Authoritative resolved runtime, test, and tooling layout."""

    runtime_sources: tuple[ProjectSource, ...]
    test_roots: tuple[ProjectPath, ...]
    tooling_sources: tuple[ProjectSource, ...]


@dataclass(frozen=True, slots=True)
class ScopedFile:
    """A Python file classified into one configured scan scope."""

    path: Path
    root: Path
    scope: ScopeName
    relative_parts: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PositionFacts:
    """Computed role and package-position facts for a scoped file."""

    relative_parts: tuple[str, ...]
    domain: str | None
    subdomain: str | None
    role: str | None
    is_entry_module: bool
    is_main_module: bool


@dataclass(frozen=True, slots=True)
class DiscoveredTree:
    """All discovered files plus the repo root they were resolved from."""

    files: tuple[ScopedFile, ...]
    repo_root: RepoRoot
    layout: ProjectLayout
