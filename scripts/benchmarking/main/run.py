"""Run end-to-end or instrumented Strata benchmarks."""

from __future__ import annotations

import sys
from pathlib import Path

from scripts.benchmarking._helpers.execution import benchmark_processes, render_benchmark
from scripts.benchmarking._helpers.profiling import profile_check
from scripts.benchmarking._helpers.rendering import render_profile
from scripts.benchmarking.exceptions import BenchmarkError
from scripts.benchmarking.models import BenchmarkReport, ProfileReport


def run_benchmark(
    *, project: Path, runs: int, profile: bool, executable: Path | None = None
) -> int:
    """Run the selected benchmark against one configured repository."""

    resolved_project: Path = project.resolve()
    if not resolved_project.is_dir():
        sys.stderr.write(f"Benchmark project does not exist: {resolved_project}\n")
        return 2
    try:
        if profile:
            report: ProfileReport = profile_check(resolved_project)
            sys.stdout.write(render_profile(report=report))
        else:
            resolved_executable: Path = (
                Path(sys.executable).with_name("strata")
                if executable is None
                else executable.resolve()
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
