"""Run one instrumented Fensu check."""

from __future__ import annotations

import os
import shutil
from collections.abc import Callable
from io import StringIO
from pathlib import Path
from typing import cast

from fensu.analysis.main.resolve_native_backend_version import resolve_native_backend_version
from fensu.cache.results._helpers.paths import relative_repository_path
from fensu.cli.main.custom_check_host import run_custom_check as run_check
from fensu.instrumentation.main.measure_operations import measure_operations
from scripts.benchmarking.classes.check_profiler import CheckProfiler
from scripts.benchmarking.models import OperationReport, ProfileReport
from scripts.benchmarking.types import OperationProfileMode

_CACHE_DIRECTORY_NAME: str = ".fensu"


def profile_check(project: Path) -> ProfileReport:
    """Profile one configured project and restore evaluator functions afterward."""

    return CheckProfiler().run(project)


def profile_operations(*, project: Path, mode: OperationProfileMode) -> OperationReport:
    """Measure deterministic operations for one uncached, cold, or warm check."""

    previous_directory: Path = Path.cwd()
    os.chdir(project)
    try:
        argv: tuple[str, ...] = _operation_argv(mode=mode)
        if mode is OperationProfileMode.COLD:
            shutil.rmtree(project / _CACHE_DIRECTORY_NAME, ignore_errors=True)
        if mode is OperationProfileMode.WARM:
            _ = run_check(argv=argv, stdout=StringIO(), stderr=StringIO())
        _clear_process_caches()
        counts: dict[str, int] = measure_operations(
            operation=lambda: run_check(argv=argv, stdout=StringIO(), stderr=StringIO())
        )
        return OperationReport(mode=mode.value, counts=tuple(sorted(counts.items())))
    finally:
        _clear_process_caches()
        os.chdir(previous_directory)


def _operation_argv(*, mode: OperationProfileMode) -> tuple[str, ...]:
    if mode is OperationProfileMode.UNCACHED:
        return ("--no-color", "--no-cache", "--jobs", "1")
    return ("--no-color", "--cache", "--jobs", "1")


def _clear_process_caches() -> None:
    resolve_native_backend_version.cache_clear()
    cache_clear: Callable[[], None] | None = cast(
        Callable[[], None] | None,
        getattr(relative_repository_path, "cache_clear", None),
    )
    if cache_clear is not None:
        cache_clear()
