"""Discover configured Python files and their position facts."""

from __future__ import annotations

import os
from pathlib import Path

from strata.analysis.main.select_fact_backend import select_fact_backend
from strata.analysis.types import FactBackend
from strata.config.models import Config
from strata.discovery._helpers.layout import build_project_layout
from strata.discovery._helpers.repo_root import resolve_repo_root
from strata.discovery._helpers.scope import discover_scoped_files
from strata.discovery.constants import SNAPSHOT_TABLE
from strata.discovery.models import DiscoveredTree, ProjectLayout, RepoRoot, ScopedFile
from strata.instrumentation.constants import OPERATION_COUNTERS, SNAPSHOT_ROOT_RELATIVIZE_OPERATION


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
        relative_by_path=_snapshot_relative_paths(repo_root=repo_root, files=files),
    )


def _snapshot_relative_paths(
    *,
    repo_root: RepoRoot,
    files: tuple[ScopedFile, ...],
) -> dict[str, str]:
    root_parts: dict[Path, tuple[str, ...] | None] = {}
    relative_by_path: dict[str, str] = {}
    repo_root_value: str = str(repo_root.path)
    repo_prefix: str = repo_root_value + os.sep
    for scoped_file in files:
        if scoped_file.root not in root_parts:
            OPERATION_COUNTERS.record(operation=SNAPSHOT_ROOT_RELATIVIZE_OPERATION)
            try:
                root_parts[scoped_file.root] = scoped_file.root.relative_to(repo_root.path).parts
            except ValueError:
                root_parts[scoped_file.root] = None
        prefix: tuple[str, ...] | None = root_parts[scoped_file.root]
        if prefix is None:
            continue
        path_value: str = str(scoped_file.path)
        if path_value != repo_root_value and not path_value.startswith(repo_prefix):
            continue
        relative_by_path[path_value] = "/".join((*prefix, *scoped_file.relative_parts))
    return relative_by_path
