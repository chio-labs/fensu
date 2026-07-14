"""Discover configured Python files and their position facts."""

from __future__ import annotations

from pathlib import Path

from strata.analysis.main.select_fact_backend import select_fact_backend
from strata.analysis.types import FactBackend
from strata.config.models import Config
from strata.discovery._helpers.layout import build_project_layout
from strata.discovery._helpers.repo_root import resolve_repo_root
from strata.discovery._helpers.scope import discover_scoped_files
from strata.discovery.constants import SNAPSHOT_TABLE
from strata.discovery.models import DiscoveredTree, ProjectLayout, RepoRoot, ScopedFile


def discover_files(*, config: Config, repo_root: Path | None = None) -> DiscoveredTree:
    """Discover Python files under configured roots, tests, and tooling paths."""

    resolved_root: RepoRoot = resolve_repo_root(path=repo_root)
    layout: ProjectLayout = build_project_layout(config=config, repo_root=resolved_root)
    files: tuple[ScopedFile, ...] = discover_scoped_files(layout=layout)
    _seed_snapshot(repo_root=resolved_root, files=files)
    return DiscoveredTree(files=files, repo_root=resolved_root, layout=layout)


def _seed_snapshot(*, repo_root: RepoRoot, files: tuple[ScopedFile, ...]) -> None:
    if select_fact_backend().backend is not FactBackend.NATIVE:
        return
    SNAPSHOT_TABLE.install(
        repo_root=repo_root.path,
        canonical_paths=tuple(scoped_file.path for scoped_file in files),
    )
