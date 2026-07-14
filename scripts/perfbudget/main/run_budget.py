"""Run every budget scenario against one freshly generated corpus."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from scripts.perfbudget._helpers.execution import cleared_cache, measured_check
from scripts.perfbudget._helpers.validation import budget_failures
from scripts.perfbudget.constants import (
    COLD_SCENARIO,
    EDIT_APPENDIX,
    EDIT_SCENARIO,
    EDITED_HELPER_FILE_NAME,
    UNCACHED_SCENARIO,
    WARM_SCENARIO,
)
from scripts.perfbudget.models import BudgetSpec, ScenarioFailure, ScenarioResult
from scripts.perfcorpus.main.generate_corpus import generate_corpus
from scripts.perfcorpus.models import CorpusSpec, CorpusSummary


def run_budget(
    *,
    files: int,
    seed: int,
    uncached_ceiling: float,
    cold_ceiling: float,
    warm_ceiling: float,
    edit_ceiling: float,
    executable: Path | None = None,
) -> int:
    """Measure all scenarios, report them, and return a pass or fail exit code."""

    spec: BudgetSpec = BudgetSpec(
        executable=executable if executable is not None else _default_executable(),
        file_target=files,
        seed=seed,
        uncached_ceiling=uncached_ceiling,
        cold_ceiling=cold_ceiling,
        warm_ceiling=warm_ceiling,
        edit_ceiling=edit_ceiling,
    )
    with tempfile.TemporaryDirectory(prefix="strata-perfbudget-") as workspace:
        project: Path = Path(workspace) / "corpus"
        summary: CorpusSummary = generate_corpus(
            spec=CorpusSpec(target=project, file_target=spec.file_target, seed=spec.seed)
        )
        results: dict[str, ScenarioResult] = _measured_scenarios(spec=spec, project=project)
    print(f"corpus_files={summary.files_written} corpus_faults={summary.faults_expected}")
    for result in results.values():
        print(
            f"scenario={result.name} seconds={result.seconds:.2f} "
            f"exit={result.exit_code} {result.cache_stats}"
        )
    failures: tuple[ScenarioFailure, ...] = budget_failures(spec=spec, results=results)
    for failure in failures:
        print(f"BUDGET FAILURE {failure.scenario}: {failure.reason}", file=sys.stderr)
    return 1 if failures else 0


def _default_executable() -> Path:
    return Path(sys.executable).parent / "strata"


def _measured_scenarios(*, spec: BudgetSpec, project: Path) -> dict[str, ScenarioResult]:
    results: dict[str, ScenarioResult] = {}
    _ = cleared_cache(project=project)
    results[UNCACHED_SCENARIO] = measured_check(
        name=UNCACHED_SCENARIO, executable=spec.executable, project=project, cache=False
    )
    _ = cleared_cache(project=project)
    results[COLD_SCENARIO] = measured_check(
        name=COLD_SCENARIO, executable=spec.executable, project=project, cache=True
    )
    results[WARM_SCENARIO] = measured_check(
        name=WARM_SCENARIO, executable=spec.executable, project=project, cache=True
    )
    edited: Path = sorted(project.rglob(EDITED_HELPER_FILE_NAME))[0]
    edited.write_text(edited.read_text(encoding="utf-8") + EDIT_APPENDIX, encoding="utf-8")
    results[EDIT_SCENARIO] = measured_check(
        name=EDIT_SCENARIO, executable=spec.executable, project=project, cache=True
    )
    return results
