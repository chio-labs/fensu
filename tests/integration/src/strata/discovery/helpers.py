"""Local helpers for discovery backend-parity tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from strata.analysis.constants import FACT_BACKEND_ENV_VARIABLE
from strata.analysis.main.select_fact_backend import select_fact_backend
from strata.config.models import Config
from strata.discovery.constants import SNAPSHOT_TABLE
from strata.discovery.main.discover_files import discover_files
from strata.discovery.models import DiscoveredTree


def write_fixture_tree(
    *,
    root: Path,
    files: tuple[str, ...],
    directory_symlinks: tuple[tuple[str, str], ...],
    file_symlinks: tuple[tuple[str, str], ...],
) -> None:
    """Create Python files and symlinks at repo-relative locations."""

    for relative in files:
        path: Path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x: int = 1\n", encoding="utf-8")
    for link, target in directory_symlinks + file_symlinks:
        link_path: Path = root / link
        link_path.parent.mkdir(parents=True, exist_ok=True)
        link_path.symlink_to(root / target)


def discovered_with_backend(
    *,
    backend: str,
    repo_root: Path,
    config: Config,
    monkeypatch: pytest.MonkeyPatch,
) -> DiscoveredTree:
    """Run discovery with one pinned fact backend and reset selection state."""

    monkeypatch.setenv(FACT_BACKEND_ENV_VARIABLE, backend)
    select_fact_backend.cache_clear()
    tree: DiscoveredTree = discover_files(config=config, repo_root=repo_root)
    select_fact_backend.cache_clear()
    SNAPSHOT_TABLE.clear()
    return tree
