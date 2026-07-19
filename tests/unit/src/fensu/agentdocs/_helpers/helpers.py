"""Filesystem setup helpers for skill identity tests."""

from collections.abc import Callable
from pathlib import Path


def write_git_marker(*, root: Path, marker_kind: str) -> None:
    """Write one supported Git metadata marker form without test-side branching."""

    writers: dict[str, Callable[[], None]] = {
        "directory": lambda: (root / ".git").mkdir(),
        "file": lambda: _write_git_file(root),
    }
    _ = writers[marker_kind]()


def _write_git_file(root: Path) -> None:
    _ = (root / ".git").write_text(
        "gitdir: /tmp/worktree-metadata\n",
        encoding="utf-8",
    )


def write_project_pyproject(*, root: Path, name: str) -> None:
    """Write one PEP 621 project identity source."""

    root.mkdir(parents=True, exist_ok=True)
    (root / "pyproject.toml").write_text(
        f'[project]\nname = "{name}"\n',
        encoding="utf-8",
    )
