"""Run end-to-end or instrumented Strata benchmarks."""

from __future__ import annotations

import sys
from pathlib import Path
from shutil import which

from scripts.benchmarking._helpers.execution import benchmark_processes, render_benchmark
from scripts.benchmarking._helpers.profiling import profile_check, profile_operations
from scripts.benchmarking._helpers.rendering import render_operations, render_profile
from scripts.benchmarking.exceptions import BenchmarkError
from scripts.benchmarking.models import BenchmarkReport, OperationReport, ProfileReport
from scripts.benchmarking.types import OperationProfileMode


def run_benchmark(
    *,
    project: Path,
    runs: int,
    profile: bool,
    operations: OperationProfileMode | None = None,
    executable: Path | None = None,
) -> int:
    """Run the selected benchmark against one configured repository."""

    resolved_project: Path = project.resolve()
    if not resolved_project.is_dir():
        sys.stderr.write(f"Benchmark project does not exist: {resolved_project}\n")
        return 2
    try:
        if operations is not None:
            operation_report: OperationReport = profile_operations(
                project=resolved_project,
                mode=operations,
            )
            sys.stdout.write(render_operations(report=operation_report))
        elif profile:
            report: ProfileReport = profile_check(resolved_project)
            sys.stdout.write(render_profile(report=report))
        else:
            resolved_executable: Path = (
                _installed_strata() if executable is None else executable.resolve()
            )
            benchmark: BenchmarkReport = benchmark_processes(
                project=resolved_project,
                executable=resolved_executable,
                runs=runs,
            )
            sys.stdout.write(render_benchmark(benchmark))
        sys.stdout.write("\n")
        return 0
    except BenchmarkError as error:
        sys.stderr.write(f"{error}\n")
        return 2


def _installed_strata() -> Path:
    located: str | None = which("strata", path=str(Path(sys.executable).parent))
    if located is None:
        raise BenchmarkError("Could not locate the installed Strata executable.")
    return Path(located)
