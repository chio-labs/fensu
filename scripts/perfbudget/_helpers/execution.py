"""Execute measured strata check scenarios against one corpus."""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import time
from pathlib import Path

from scripts.perfbudget.models import ScenarioResult

_CACHE_DIRECTORY_NAME: str = ".strata"
_STATS_PREFIX: str = "Cache:"


def measured_check(
    *,
    name: str,
    executable: Path,
    project: Path,
    cache: bool,
) -> ScenarioResult:
    """Run one timed strata check and capture its output identity and stats."""

    cache_flag: str = "--cache" if cache else "--no-cache"
    started: float = time.perf_counter()
    completed: subprocess.CompletedProcess[str] = subprocess.run(
        [str(executable), "check", cache_flag, "--cache-stats", "--no-color"],
        cwd=project,
        capture_output=True,
        text=True,
        check=False,
    )
    elapsed: float = time.perf_counter() - started
    return ScenarioResult(
        name=name,
        seconds=elapsed,
        exit_code=completed.returncode,
        output_sha256=hashlib.sha256(completed.stdout.encode("utf-8")).hexdigest(),
        cache_stats=_stats_line(stderr=completed.stderr),
    )


def cleared_cache(*, project: Path) -> Path:
    """Remove the project cache directory and return its path."""

    cache_directory: Path = project / _CACHE_DIRECTORY_NAME
    shutil.rmtree(cache_directory, ignore_errors=True)
    return cache_directory


def _stats_line(*, stderr: str) -> str:
    lines: list[str] = []
    for line in stderr.splitlines():
        if line.startswith(_STATS_PREFIX):
            lines.append(line.strip())
    return " ".join(lines)
