"""Run one instrumented Strata check."""

from __future__ import annotations

from pathlib import Path

from scripts.benchmarking.classes.check_profiler import CheckProfiler
from scripts.benchmarking.models import ProfileReport


def profile_check(project: Path) -> ProfileReport:
    """Profile one configured project and restore evaluator functions afterward."""

    return CheckProfiler().run(project)
