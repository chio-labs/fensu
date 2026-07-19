"""Execute and summarize complete Fensu check processes."""

from __future__ import annotations

import hashlib
import statistics
import subprocess
import time
from pathlib import Path

from scripts.benchmarking.exceptions import BenchmarkError
from scripts.benchmarking.models import BenchmarkReport, CheckRun

_allowed_check_return_codes: frozenset[int] = frozenset({0, 1})


def benchmark_processes(*, project: Path, executable: Path, runs: int) -> BenchmarkReport:
    """Warm the executable, measure complete checks, and verify stable diagnostics."""

    if runs < 1:
        raise BenchmarkError("Benchmark runs must be at least one.")
    warmup: CheckRun = _run_check(project=project, executable=executable)
    measured: tuple[CheckRun, ...] = tuple(
        _run_check(project=project, executable=executable) for _index in range(runs)
    )
    expected_output: bytes = warmup.output
    if any(run.output != expected_output for run in measured):
        raise BenchmarkError("Benchmark diagnostics changed between measured runs.")
    return BenchmarkReport(
        elapsed_seconds=tuple(run.elapsed_seconds for run in measured),
        output_sha256=hashlib.sha256(expected_output).hexdigest(),
        output_bytes=len(expected_output),
        fault_summary=_fault_summary(expected_output),
    )


def render_benchmark(report: BenchmarkReport) -> str:
    """Render stable process timings and diagnostic identity."""

    runs: str = ", ".join(f"{elapsed:.2f}" for elapsed in report.elapsed_seconds)
    return "\n".join(
        (
            f"runs_seconds={runs}",
            f"median_seconds={statistics.median(report.elapsed_seconds):.2f}",
            f"output_bytes={report.output_bytes}",
            f"output_sha256={report.output_sha256}",
            f"summary={report.fault_summary}",
        )
    )


def _run_check(*, project: Path, executable: Path) -> CheckRun:
    started: float = time.perf_counter()
    try:
        completed: subprocess.CompletedProcess[bytes] = subprocess.run(
            (str(executable), "check", "--no-color"),
            cwd=project,
            capture_output=True,
            check=False,
        )
    except OSError as error:
        raise BenchmarkError(f"Could not execute Fensu check at {executable}: {error}") from error
    elapsed: float = time.perf_counter() - started
    if completed.returncode not in _allowed_check_return_codes:
        error: str = completed.stderr.decode("utf-8", errors="replace").strip()
        raise BenchmarkError(
            f"Fensu check exited {completed.returncode}: {error or 'no error output'}"
        )
    return CheckRun(
        elapsed_seconds=elapsed,
        output=completed.stdout,
        return_code=completed.returncode,
    )


def _fault_summary(output: bytes) -> str:
    lines: list[str] = output.decode("utf-8", errors="replace").splitlines()
    return lines[-1] if lines else "no output"
