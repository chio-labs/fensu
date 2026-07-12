"""Discover configured Python files and their position facts."""

from __future__ import annotations

from pathlib import Path

from strata.config.models import Config
from strata.discovery.helpers.layout import build_project_layout
from strata.discovery.helpers.repo_root import resolve_repo_root
from strata.discovery.helpers.scope import discover_scoped_files
from strata.discovery.models import DiscoveredTree, ProjectLayout, RepoRoot, ScopedFile


def discover_files(*, config: Config, repo_root: Path | None = None) -> DiscoveredTree:
    """Discover Python files under configured roots, tests, and tooling paths."""

    resolved_root: RepoRoot = resolve_repo_root(path=repo_root)
    layout: ProjectLayout = build_project_layout(config=config, repo_root=resolved_root)
    files: tuple[ScopedFile, ...] = discover_scoped_files(layout=layout)
    return DiscoveredTree(files=files, repo_root=resolved_root, layout=layout)
