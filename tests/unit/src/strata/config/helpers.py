"""Helpers for config loading tests."""

from __future__ import annotations

from pathlib import Path


def write_strata_toml(*, root: Path, contents: str) -> Path:
    """Write a dedicated strata.toml config file."""

    path: Path = root / "strata.toml"
    path.write_text(contents, encoding="utf-8")
    return path


def write_pyproject_toml(*, root: Path, contents: str) -> Path:
    """Write a pyproject.toml config file."""

    path: Path = root / "pyproject.toml"
    path.write_text(contents, encoding="utf-8")
    return path
