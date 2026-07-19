"""Local helpers for native discovery tests."""

from __future__ import annotations

from pathlib import Path

from fensu.config.models import Config
from fensu.discovery.constants import SNAPSHOT_TABLE
from fensu.discovery.main.discover_files import discover_files
from fensu.discovery.models import DiscoveredTree


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


def discovered_tree(*, repo_root: Path, config: Config) -> DiscoveredTree:
    """Run native discovery and clear its process-wide snapshot afterward."""

    tree: DiscoveredTree = discover_files(config=config, repo_root=repo_root)
    SNAPSHOT_TABLE.clear()
    return tree
