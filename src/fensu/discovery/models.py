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
class OwnershipRoot:
    """One concrete directory where domain ownership begins."""

    path: Path
    relative_parts: tuple[str, ...]
    declaration: str


@dataclass(frozen=True, slots=True)
class ProjectLayout:
    """Authoritative resolved runtime, test, and tooling layout."""

    runtime_sources: tuple[ProjectSource, ...]
    test_roots: tuple[ProjectPath, ...]
    tooling_sources: tuple[ProjectSource, ...]
    ownership_roots: tuple[OwnershipRoot, ...] = ()


@dataclass(frozen=True, slots=True)
class ScopedFile:
    """A Python file classified into one configured scan scope."""

    path: Path
    root: Path
    scope: ScopeName
    relative_parts: tuple[str, ...]
    ownership_root: Path | None = None
    ownership_root_declaration: str | None = None
    ownership_relative_parts: tuple[str, ...] | None = None

    def ownership_parts(self) -> tuple[str, ...]:
        """Return ownership-relative parts or the physical fallback for synthetic files."""

        return (
            self.relative_parts
            if self.ownership_relative_parts is None
            else self.ownership_relative_parts
        )


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
    project_root: RepoRoot | None = None
