"""Local helpers for operation-count invariant tests."""

from __future__ import annotations

from io import StringIO
from pathlib import Path

from strata.analysis.main.resolve_native_backend_version import resolve_native_backend_version
from strata.cache.results._helpers.paths import relative_repository_path
from strata.cli.main.check import run_check
from strata.instrumentation.main.measure_operations import measure_operations


def _no_cache_to_clear() -> None:
    """Stand in for cache_clear when memoization is absent."""


def counted_check(*, argv: tuple[str, ...]) -> dict[str, int]:
    """Run one in-process check and return its operation counts."""

    resolve_native_backend_version.cache_clear()
    getattr(relative_repository_path, "cache_clear", _no_cache_to_clear)()
    counts: dict[str, int] = measure_operations(
        operation=lambda: run_check(argv=argv, stdout=StringIO())
    )
    resolve_native_backend_version.cache_clear()
    return counts


def python_file_count(*, root: Path) -> int:
    """Return how many Python files the corpus evaluates."""

    return len(list(root.rglob("*.py")))


def appended_module_constant(*, path: Path) -> Path:
    """Append one module constant to a source file and return the path."""

    path.write_text(path.read_text(encoding="utf-8") + "\nEDIT_MARKER: int = 1\n", encoding="utf-8")
    return path


def append_source_newlines(*, root: Path) -> tuple[Path, ...]:
    """Change every Python source by appending semantically inert whitespace."""

    paths: tuple[Path, ...] = tuple(sorted(root.rglob("*.py")))
    for path in paths:
        path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    return paths
