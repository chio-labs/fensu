"""Discovery models: repository root, scoped files, and discovered trees."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from strata.discovery.core.types import ScopeName


@dataclass(frozen=True, slots=True)
class RepoRoot:
    """The resolved repository root used for config-relative discovery."""

    path: Path


@dataclass(frozen=True, slots=True)
class ScopedFile:
    """A Python file classified into one configured scan scope."""

    path: Path
    root: Path
    scope: ScopeName
    relative_parts: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DiscoveredTree:
    """All discovered files plus the repo root they were resolved from."""

    files: tuple[ScopedFile, ...]
    repo_root: RepoRoot
