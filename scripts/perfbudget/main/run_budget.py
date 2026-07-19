"""Run every budget scenario against freshly generated corpora."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from statistics import median

from scripts.perfbudget._helpers.execution import (
    dense_scenarios,
    standard_scenarios,
    startup_scenarios,
)
from scripts.perfbudget._helpers.specification import resolved_budget_spec
from scripts.perfbudget._helpers.validation import budget_failures, repeated_run_failures
from scripts.perfbudget.constants import DENSE_FAULT_EVERY
from scripts.perfbudget.models import (
    BudgetMeasurement,
    BudgetSpec,
    ScenarioFailure,
    ScenarioResult,
)
from scripts.perfcorpus.main.generate_corpus import generate_corpus
from scripts.perfcorpus.models import CorpusSpec, CorpusSummary


def run_budget(
    *,
    files: int,
    seed: int,
    uncached_ceiling: float | None,
    cold_ceiling: float | None,
    warm_ceiling: float | None,
    edit_ceiling: float | None,
    version_ceiling: float | None,
    init_ceiling: float | None,
    runs: int = 1,
    executable: Path | None = None,
) -> int:
    """Measure all scenarios, report them, and return a pass or fail exit code."""

    spec: BudgetSpec = resolved_budget_spec(
        files=files,
        seed=seed,
        uncached_ceiling=uncached_ceiling,
        cold_ceiling=cold_ceiling,
        warm_ceiling=warm_ceiling,
        edit_ceiling=edit_ceiling,
        version_ceiling=version_ceiling,
        init_ceiling=init_ceiling,
        executable=executable,
    )
    if runs < 1:
        print("BUDGET FAILURE runs: runs must be at least one", file=sys.stderr)
        return 1
    with tempfile.TemporaryDirectory(prefix="strata-perfbudget-") as workspace:
        measurement: BudgetMeasurement = _measured_runs(
            spec=spec,
            runs=runs,
            workspace=Path(workspace),
        )
    print(
        f"runs={runs} corpus_files={measurement.corpus_files} "
        f"corpus_faults={measurement.corpus_faults} dense_faults={measurement.dense_faults}"
    )
    _render_runs(runs=measurement.runs)
    failures: list[ScenarioFailure] = []
    for index, results in enumerate(measurement.runs, start=1):
        for failure in budget_failures(spec=spec, results=results):
            failures.append(
                ScenarioFailure(
                    scenario=f"{failure.scenario}[run={index}]",
                    reason=failure.reason,
                )
            )
    failures.extend(repeated_run_failures(runs=measurement.runs))
    for failure in failures:
        print(f"BUDGET FAILURE {failure.scenario}: {failure.reason}", file=sys.stderr)
    return 1 if failures else 0


def _measured_runs(*, spec: BudgetSpec, runs: int, workspace: Path) -> BudgetMeasurement:
    measured: list[dict[str, ScenarioResult]] = []
    corpus_files: int = 0
    corpus_faults: int = 0
    dense_faults: int = 0
    for index in range(runs):
        project: Path = workspace / f"corpus-{index}"
        summary: CorpusSummary = generate_corpus(
            spec=CorpusSpec(target=project, file_target=spec.file_target, seed=spec.seed)
        )
        results: dict[str, ScenarioResult] = standard_scenarios(spec=spec, project=project)
        dense_project: Path = workspace / f"dense-{index}"
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
        init_project: Path = workspace / f"init-{index}"
        _ = generate_corpus(
            spec=CorpusSpec(target=init_project, file_target=spec.file_target, seed=spec.seed)
        )
        results.update(startup_scenarios(spec=spec, project=init_project))
        measured.append(results)
        corpus_files = summary.files_written
        corpus_faults = summary.faults_expected
        dense_faults = dense_summary.faults_expected
    return BudgetMeasurement(
        corpus_files=corpus_files,
        corpus_faults=corpus_faults,
        dense_faults=dense_faults,
        runs=tuple(measured),
    )


def _render_runs(*, runs: tuple[dict[str, ScenarioResult], ...]) -> None:
    for name in runs[0]:
        results: tuple[ScenarioResult, ...] = tuple(run[name] for run in runs)
        seconds: str = ",".join(f"{result.seconds:.2f}" for result in results)
        reference: ScenarioResult = results[0]
        rss_values: tuple[int, ...] = tuple(
            result.max_rss_kib for result in results if result.max_rss_kib is not None
        )
        max_rss: str = str(max(rss_values)) if rss_values else "unavailable"
        print(
            f"scenario={name} runs_seconds={seconds} median_seconds="
            f"{median(result.seconds for result in results):.2f} exit={reference.exit_code} "
            f"max_rss_kib={max_rss} output_sha256={reference.output_sha256} "
            f"{reference.cache_stats}"
        )
