"""Execute measured strata check scenarios against one corpus."""

from __future__ import annotations

import hashlib
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from scripts.perfbudget.constants import (
    CHURN_1_PERCENT_SCENARIO,
    CHURN_25_PERCENT_SCENARIO,
    CHURN_75_PERCENT_SCENARIO,
    CHURN_100_PERCENT_SCENARIO,
    CHURN_APPENDIX,
    CHURN_UNCACHED_SCENARIO,
    COLD_SCENARIO,
    DENSE_COLD_SCENARIO,
    DENSE_WARM_SCENARIO,
    EDIT_APPENDIX,
    EDIT_SCENARIO,
    EDITED_HELPER_FILE_NAME,
    GLOBAL_MISMATCH_CONFIG_APPENDIX,
    GLOBAL_MISMATCH_SCENARIO,
    GLOBAL_MISMATCH_UNCACHED_SCENARIO,
    UNCACHED_SCENARIO,
    WARM_SCENARIO,
)
from scripts.perfbudget.models import BudgetSpec, ScenarioResult

_CACHE_DIRECTORY_NAME: str = ".strata"
_STATS_PREFIX: str = "Cache:"
_GNU_TIME_PATH: Path = Path("/usr/bin/time")


def standard_scenarios(*, spec: BudgetSpec, project: Path) -> dict[str, ScenarioResult]:
    """Measure the complete deterministic cache-change scenario matrix."""

    results: dict[str, ScenarioResult] = {}
    _ = cleared_cache(project=project)
    results[UNCACHED_SCENARIO] = measured_check(
        name=UNCACHED_SCENARIO,
        executable=spec.executable,
        project=project,
        cache=False,
    )
    _ = cleared_cache(project=project)
    results[COLD_SCENARIO] = measured_check(
        name=COLD_SCENARIO,
        executable=spec.executable,
        project=project,
        cache=True,
    )
    results[WARM_SCENARIO] = measured_check(
        name=WARM_SCENARIO,
        executable=spec.executable,
        project=project,
        cache=True,
    )
    edited: Path = sorted(project.rglob(EDITED_HELPER_FILE_NAME))[0]
    edited.write_text(edited.read_text(encoding="utf-8") + EDIT_APPENDIX, encoding="utf-8")
    results[EDIT_SCENARIO] = measured_check(
        name=EDIT_SCENARIO,
        executable=spec.executable,
        project=project,
        cache=True,
    )
    _change_source_ratio(project=project, numerator=1, denominator=100)
    results[CHURN_1_PERCENT_SCENARIO] = measured_check(
        name=CHURN_1_PERCENT_SCENARIO,
        executable=spec.executable,
        project=project,
        cache=True,
    )
    _change_source_ratio(project=project, numerator=25, denominator=100)
    results[CHURN_25_PERCENT_SCENARIO] = measured_check(
        name=CHURN_25_PERCENT_SCENARIO,
        executable=spec.executable,
        project=project,
        cache=True,
    )
    _change_source_ratio(project=project, numerator=75, denominator=100)
    results[CHURN_75_PERCENT_SCENARIO] = measured_check(
        name=CHURN_75_PERCENT_SCENARIO,
        executable=spec.executable,
        project=project,
        cache=True,
    )
    _change_source_ratio(project=project, numerator=100, denominator=100)
    results[CHURN_100_PERCENT_SCENARIO] = measured_check(
        name=CHURN_100_PERCENT_SCENARIO,
        executable=spec.executable,
        project=project,
        cache=True,
    )
    results[CHURN_UNCACHED_SCENARIO] = measured_check(
        name=CHURN_UNCACHED_SCENARIO,
        executable=spec.executable,
        project=project,
        cache=False,
    )
    config_path: Path = project / "strata.toml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8") + GLOBAL_MISMATCH_CONFIG_APPENDIX,
        encoding="utf-8",
    )
    results[GLOBAL_MISMATCH_SCENARIO] = measured_check(
        name=GLOBAL_MISMATCH_SCENARIO,
        executable=spec.executable,
        project=project,
        cache=True,
    )
    results[GLOBAL_MISMATCH_UNCACHED_SCENARIO] = measured_check(
        name=GLOBAL_MISMATCH_UNCACHED_SCENARIO,
        executable=spec.executable,
        project=project,
        cache=False,
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
    )
    results[DENSE_WARM_SCENARIO] = measured_check(
        name=DENSE_WARM_SCENARIO,
        executable=spec.executable,
        project=project,
        cache=True,
    )
    return results


def measured_check(
    *,
    name: str,
    executable: Path,
    project: Path,
    cache: bool,
) -> ScenarioResult:
    """Run one timed strata check and capture its output identity and stats."""

    cache_flag: str = "--cache" if cache else "--no-cache"
    command: list[str] = [
        str(executable),
        "check",
        cache_flag,
        "--cache-stats",
        "--no-color",
        "--jobs",
        "1",
    ]
    timing_path: Path | None = _timing_path()
    if timing_path is not None:
        command = [
            str(_GNU_TIME_PATH),
            "-f",
            "%M",
            "-o",
            str(timing_path),
            *command,
        ]
    started: float = time.perf_counter()
    try:
        completed: subprocess.CompletedProcess[str] = subprocess.run(
            command,
            cwd=project,
            capture_output=True,
            text=True,
            check=False,
        )
        max_rss_kib: int | None = _read_max_rss(timing_path=timing_path)
    finally:
        if timing_path is not None:
            timing_path.unlink(missing_ok=True)
    elapsed: float = time.perf_counter() - started
    return ScenarioResult(
        name=name,
        seconds=elapsed,
        exit_code=completed.returncode,
        output_sha256=hashlib.sha256(completed.stdout.encode("utf-8")).hexdigest(),
        cache_stats=_stats_line(stderr=completed.stderr),
        max_rss_kib=max_rss_kib,
    )


def cleared_cache(*, project: Path) -> Path:
    """Remove the project cache directory and return its path."""

    cache_directory: Path = project / _CACHE_DIRECTORY_NAME
    shutil.rmtree(cache_directory, ignore_errors=True)
    return cache_directory


def _change_source_ratio(*, project: Path, numerator: int, denominator: int) -> tuple[Path, ...]:
    paths: tuple[Path, ...] = tuple(sorted(project.rglob("*.py")))
    changed_count: int = max(1, math.ceil(len(paths) * numerator / denominator))
    changed: tuple[Path, ...] = paths[:changed_count]
    for path in changed:
        path.write_text(path.read_text(encoding="utf-8") + CHURN_APPENDIX, encoding="utf-8")
    return changed


def _timing_path() -> Path | None:
    if not sys.platform.startswith("linux") or not _GNU_TIME_PATH.is_file():
        return None
    created: tuple[int, str] = tempfile.mkstemp(
        prefix="strata-perfbudget-rss-",
    )
    descriptor: int = created[0]
    path: Path = Path(created[1])
    os.close(descriptor)
    return path


def _read_max_rss(*, timing_path: Path | None) -> int | None:
    if timing_path is None:
        return None
    try:
        lines: list[str] = timing_path.read_text(encoding="utf-8").splitlines()
        value: str = lines[-1].strip() if lines else ""
        return int(value) if value else None
    except (OSError, ValueError):
        return None


def _stats_line(*, stderr: str) -> str:
    lines: list[str] = []
    for line in stderr.splitlines():
        if line.startswith(_STATS_PREFIX):
            lines.append(line.strip())
    return " ".join(lines)
