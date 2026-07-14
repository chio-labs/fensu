"""Execute measured strata check scenarios against one corpus."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import time
from pathlib import Path

from scripts.perfbudget.constants import (
    COLD_SCENARIO,
    DENSE_COLD_SCENARIO,
    DENSE_WARM_SCENARIO,
    EDIT_APPENDIX,
    EDIT_SCENARIO,
    EDITED_HELPER_FILE_NAME,
    UNCACHED_SCENARIO,
    WARM_SCENARIO,
)
from scripts.perfbudget.models import BudgetSpec, ScenarioResult
from strata.analysis.constants import FACT_BACKEND_ENV_VARIABLE

_CACHE_DIRECTORY_NAME: str = ".strata"
_STATS_PREFIX: str = "Cache:"
_FALLBACK_WARNING_FRAGMENT: str = "fact backend was requested but"


def standard_scenarios(*, spec: BudgetSpec, project: Path) -> dict[str, ScenarioResult]:
    """Measure the uncached, cold, warm, and one-edit scenarios in order."""

    results: dict[str, ScenarioResult] = {}
    _ = cleared_cache(project=project)
    results[UNCACHED_SCENARIO] = measured_check(
        name=UNCACHED_SCENARIO,
        executable=spec.executable,
        project=project,
        cache=False,
        backend=spec.backend,
    )
    _ = cleared_cache(project=project)
    results[COLD_SCENARIO] = measured_check(
        name=COLD_SCENARIO,
        executable=spec.executable,
        project=project,
        cache=True,
        backend=spec.backend,
    )
    results[WARM_SCENARIO] = measured_check(
        name=WARM_SCENARIO,
        executable=spec.executable,
        project=project,
        cache=True,
        backend=spec.backend,
    )
    edited: Path = sorted(project.rglob(EDITED_HELPER_FILE_NAME))[0]
    edited.write_text(edited.read_text(encoding="utf-8") + EDIT_APPENDIX, encoding="utf-8")
    results[EDIT_SCENARIO] = measured_check(
        name=EDIT_SCENARIO,
        executable=spec.executable,
        project=project,
        cache=True,
        backend=spec.backend,
    )
    return results


def dense_scenarios(*, spec: BudgetSpec, project: Path) -> dict[str, ScenarioResult]:
    """Measure cold and warm scenarios against the fault-dense corpus."""

    results: dict[str, ScenarioResult] = {}
    _ = cleared_cache(project=project)
    results[DENSE_COLD_SCENARIO] = measured_check(
        name=DENSE_COLD_SCENARIO,
        executable=spec.executable,
        project=project,
        cache=True,
        backend=spec.backend,
    )
    results[DENSE_WARM_SCENARIO] = measured_check(
        name=DENSE_WARM_SCENARIO,
        executable=spec.executable,
        project=project,
        cache=True,
        backend=spec.backend,
    )
    return results


def measured_check(
    *,
    name: str,
    executable: Path,
    project: Path,
    cache: bool,
    backend: str,
) -> ScenarioResult:
    """Run one timed strata check and capture its output identity and stats."""

    cache_flag: str = "--cache" if cache else "--no-cache"
    environment: dict[str, str] = {**os.environ, FACT_BACKEND_ENV_VARIABLE: backend}
    started: float = time.perf_counter()
    completed: subprocess.CompletedProcess[str] = subprocess.run(
        [str(executable), "check", cache_flag, "--cache-stats", "--no-color"],
        cwd=project,
        capture_output=True,
        text=True,
        check=False,
        env=environment,
    )
    elapsed: float = time.perf_counter() - started
    return ScenarioResult(
        name=name,
        seconds=elapsed,
        exit_code=completed.returncode,
        output_sha256=hashlib.sha256(completed.stdout.encode("utf-8")).hexdigest(),
        cache_stats=_stats_line(stderr=completed.stderr),
        fallback_warned=_FALLBACK_WARNING_FRAGMENT in completed.stderr,
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
