"""Fault collection and stable ordering helpers."""

from __future__ import annotations

from pathlib import Path

from strata.rules.authoring.models import Fault


def sort_faults(*, faults: list[Fault], repo_root: Path) -> tuple[Fault, ...]:
    """Return faults sorted by path, line, column, and code."""

    return tuple(
        sorted(faults, key=lambda fault: _fault_sort_key(fault=fault, repo_root=repo_root))
    )


def _fault_sort_key(*, fault: Fault, repo_root: Path) -> tuple[str, int, int, str]:
    try:
        relative_path: Path = fault.path.relative_to(repo_root)
    except ValueError:
        relative_path = fault.path
    line: int = -1 if fault.line is None else fault.line
    column: int = -1 if fault.column is None else fault.column
    return (relative_path.as_posix(), line, column, fault.code)
