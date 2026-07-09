"""Discover configured Python files and their position facts."""

from __future__ import annotations

from strata.config.core.models import Config
from strata.discovery.core.helpers.repo_root import resolve_repo_root
from strata.discovery.core.helpers.scope import discover_scoped_files
from strata.discovery.core.models import DiscoveredTree, RepoRoot, ScopedFile


def discover_files(config: Config) -> DiscoveredTree:
    """Discover Python files under configured roots, tests, and tooling paths."""

    repo_root: RepoRoot = resolve_repo_root(config)
    files: tuple[ScopedFile, ...] = discover_scoped_files(config=config, repo_root=repo_root)
    return DiscoveredTree(files=files, repo_root=repo_root)
