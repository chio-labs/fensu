"""Run every budget scenario against freshly generated corpora."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from scripts.perfbudget._helpers.execution import dense_scenarios, standard_scenarios
from scripts.perfbudget._helpers.specification import (
    is_native_backend_available,
    resolved_budget_spec,
)
from scripts.perfbudget._helpers.validation import budget_failures
from scripts.perfbudget.constants import DENSE_FAULT_EVERY
from scripts.perfbudget.models import BudgetSpec, ScenarioFailure, ScenarioResult
from scripts.perfcorpus.main.generate_corpus import generate_corpus
from scripts.perfcorpus.models import CorpusSpec, CorpusSummary
from strata.analysis.types import FactBackend


def run_budget(
    *,
    backend: str,
    files: int,
    seed: int,
    uncached_ceiling: float | None,
    cold_ceiling: float | None,
    warm_ceiling: float | None,
    edit_ceiling: float | None,
    executable: Path | None = None,
) -> int:
    """Measure all scenarios, report them, and return a pass or fail exit code."""

    spec: BudgetSpec = resolved_budget_spec(
        backend=backend,
        files=files,
        seed=seed,
        uncached_ceiling=uncached_ceiling,
        cold_ceiling=cold_ceiling,
        warm_ceiling=warm_ceiling,
        edit_ceiling=edit_ceiling,
        executable=executable,
    )
    if spec.backend == FactBackend.NATIVE and not is_native_backend_available():
        print(
            f"BUDGET FAILURE backend: the {FactBackend.NATIVE.value} fact backend "
            "was requested but is not installed",
            file=sys.stderr,
        )
        return 1
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
        f"backend={spec.backend} corpus_files={summary.files_written} "
        f"corpus_faults={summary.faults_expected} dense_faults={dense_summary.faults_expected}"
    )
    for result in results.values():
        print(
            f"scenario={result.name} seconds={result.seconds:.2f} "
            f"exit={result.exit_code} output_sha256={result.output_sha256} {result.cache_stats}"
        )
    failures: tuple[ScenarioFailure, ...] = budget_failures(spec=spec, results=results)
    for failure in failures:
        print(f"BUDGET FAILURE {failure.scenario}: {failure.reason}", file=sys.stderr)
    return 1 if failures else 0
