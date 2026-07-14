"""Run every budget scenario against freshly generated corpora."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from scripts.perfbudget._helpers.execution import dense_scenarios, standard_scenarios
from scripts.perfbudget._helpers.validation import budget_failures
from scripts.perfbudget.constants import DENSE_FAULT_EVERY
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
        results: dict[str, ScenarioResult] = standard_scenarios(spec=spec, project=project)
        dense_project: Path = Path(workspace) / "dense"
        dense_summary: CorpusSummary = generate_corpus(
            spec=CorpusSpec(
                target=dense_project,
                file_target=spec.file_target,
                seed=spec.seed,
                annotation_fault_every=DENSE_FAULT_EVERY,
                magic_fault_every=DENSE_FAULT_EVERY,
            )
        )
        results.update(dense_scenarios(spec=spec, project=dense_project))
    print(
        f"corpus_files={summary.files_written} corpus_faults={summary.faults_expected} "
        f"dense_faults={dense_summary.faults_expected}"
    )
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
