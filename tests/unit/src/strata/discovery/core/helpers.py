"""Helpers for discovery tests."""

from __future__ import annotations

from pathlib import Path

from strata.config.core.models import Config
from strata.discovery.core.models import ScopedFile
from tests.unit.src.strata.discovery.core._test_types import LayoutConfigErrorTestCase


def write_python_files(*, root: Path, relative_paths: tuple[str, ...]) -> None:
    """Create Python files at repo-relative paths."""

    for relative_path in relative_paths:
        path: Path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x: int = 1\n", encoding="utf-8")


def make_config(
    *,
    roots: tuple[str, ...] = ("src/pkg",),
    tests: tuple[str, ...] = (),
    tooling: tuple[str, ...] = (),
) -> Config:
    """Build a Config for discovery tests without invoking the config loader."""

    return Config(roots=roots, tests=tests, tooling=tooling)


def only_file(*, files: tuple[ScopedFile, ...]) -> ScopedFile:
    """Return the only discovered file from a test fixture."""

    if len(files) != 1:
        raise AssertionError(f"Expected one discovered file, got {len(files)}")
    return files[0]


def relative_file_names(*, repo_root: Path, files: tuple[ScopedFile, ...]) -> tuple[str, ...]:
    """Return repo-relative POSIX file paths for stable assertions."""

    return tuple(file.path.relative_to(repo_root).as_posix() for file in files)


def layout_error_config(*, test_case: LayoutConfigErrorTestCase, external_root: Path) -> Config:
    """Build the invalid layout selected by a discovery test case."""

    if test_case.uses_external_root:
        return make_config(roots=(str(external_root),))
    return make_config(
        roots=test_case.roots,
        tests=test_case.tests,
        tooling=test_case.tooling,
    )
