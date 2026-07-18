"""Run one full evaluation across deterministic worker partitions."""

from __future__ import annotations

import multiprocessing
import os
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from pathlib import Path

from strata.analysis.models import ProjectDependency
from strata.config.main.load_project_config import load_project_config
from strata.config.models import Config
from strata.discovery.main.discover_files import discover_files
from strata.discovery.models import DiscoveredTree
from strata.evaluation.exceptions import ParseError
from strata.evaluation.main._evaluate_partition import evaluate_partition
from strata.evaluation.main.build_targets import build_evaluation_targets
from strata.evaluation.main.collect_result import collect_file_evaluations
from strata.evaluation.main.select_files import select_evaluation_files
from strata.evaluation.models import (
    EvaluationResult,
    EvaluationSelection,
    EvaluationTarget,
    EvaluationWorkerOutcome,
    EvaluationWorkerParseFailure,
    EvaluationWorkerRequest,
    FileEvaluation,
    PartitionEvaluation,
)
from strata.instrumentation.constants import (
    EVALUATION_WORKER_PARTITION_OPERATION,
    OPERATION_COUNTERS,
)
from strata.rules.authoring.models import CustomRuleRegistration, RuleSpec
from strata.rules.catalog.main.build_check_rule_selection import build_check_rule_selection
from strata.rules.catalog.models import RuleSelection

_WORKER_START_METHOD: str = "spawn"
_NATIVE_THREAD_ENV_VARIABLE: str = "RAYON_NUM_THREADS"
_MAXIMUM_AUTO_WORKERS: int = 8
_MINIMUM_PARALLEL_TARGETS: int = 200


def default_worker_count(*, target_count: int) -> int:
    """Return the measured-breakeven automatic worker count for one full evaluation."""

    if target_count < _MINIMUM_PARALLEL_TARGETS:
        return 1
    return max(1, min(_MAXIMUM_AUTO_WORKERS, os.cpu_count() or 1))


def parallel_full_evaluation(
    *,
    tree: DiscoveredTree,
    config: Config,
    ruleset: tuple[RuleSpec, ...],
    warning_rules: tuple[RuleSpec, ...] = (),
    custom_rule_registrations: tuple[CustomRuleRegistration, ...] = (),
    jobs: int,
) -> EvaluationResult:
    """Evaluate every target across worker processes and collect deterministically."""

    selection: EvaluationSelection = select_evaluation_files(tree=tree, config=config.evaluation)
    targets: tuple[EvaluationTarget, ...] = build_evaluation_targets(
        tree=tree,
        selection=selection,
        ruleset=ruleset,
        warning_rules=warning_rules,
        custom_rule_registrations=custom_rule_registrations,
    )
    ordered_paths: tuple[str, ...] = tuple(str(target.scoped_file.path) for target in targets)
    partitions: tuple[tuple[str, ...], ...] = _contiguous_partitions(paths=ordered_paths, jobs=jobs)
    requests: tuple[EvaluationWorkerRequest, ...] = tuple(
        EvaluationWorkerRequest(
            repo_root=str(tree.repo_root.path),
            roots=config.roots,
            cache_enabled=config.cache.enabled,
            warn=bool(warning_rules),
            native_threads=_native_threads_per_worker(worker_count=len(partitions)),
            partition=partition,
        )
        for partition in partitions
    )
    OPERATION_COUNTERS.record(
        operation=EVALUATION_WORKER_PARTITION_OPERATION,
        amount=len(requests),
    )
    outcomes: tuple[EvaluationWorkerOutcome, ...] = _run_workers(requests=requests)
    _raise_worker_parse_failure(outcomes=outcomes)
    return collect_file_evaluations(
        file_evaluations=_ordered_evaluations(outcomes=outcomes, ordered_paths=ordered_paths),
        dependencies=_merged_dependencies(outcomes=outcomes),
        config=config,
        repo_root=tree.repo_root.path,
        evaluated_rule_codes=frozenset(rule.code for rule in (*ruleset, *warning_rules)),
        selection=selection,
    )


def evaluate_worker_partition(request: EvaluationWorkerRequest) -> EvaluationWorkerOutcome:
    """Evaluate one target partition after rebuilding its discovered rule context."""

    os.environ[_NATIVE_THREAD_ENV_VARIABLE] = str(request.native_threads)
    project_dir: Path = Path(request.repo_root)
    loaded_config: Config = load_project_config(project_dir).config
    config: Config = replace(
        loaded_config,
        roots=request.roots,
        cache=replace(loaded_config.cache, enabled=request.cache_enabled),
    )
    rule_selection: RuleSelection = build_check_rule_selection(
        config=config,
        repo_root=project_dir,
        include_warnings=request.warn,
    )
    tree: DiscoveredTree = discover_files(config=config, repo_root=project_dir)
    try:
        partition_evaluation: PartitionEvaluation = evaluate_partition(
            tree=tree,
            ruleset=rule_selection.blocking,
            warning_rules=rule_selection.warnings if request.warn else (),
            config=config,
            custom_rule_registrations=rule_selection.custom_registrations,
            partition=frozenset(request.partition),
        )
    except ParseError as error:
        return EvaluationWorkerOutcome(
            file_evaluations=(),
            dependencies=(),
            parse_failure=EvaluationWorkerParseFailure(
                path=str(error.path),
                message=error.message,
                line=error.line,
                column=error.column,
            ),
        )
    return EvaluationWorkerOutcome(
        file_evaluations=partition_evaluation.file_evaluations,
        dependencies=partition_evaluation.dependencies,
        parse_failure=None,
    )


def _run_workers(
    *, requests: tuple[EvaluationWorkerRequest, ...]
) -> tuple[EvaluationWorkerOutcome, ...]:
    if len(requests) == 1:
        return (evaluate_worker_partition(requests[0]),)
    context: multiprocessing.context.BaseContext = multiprocessing.get_context(_WORKER_START_METHOD)
    with ProcessPoolExecutor(max_workers=len(requests), mp_context=context) as pool:
        return tuple(pool.map(evaluate_worker_partition, requests))


def _ordered_evaluations(
    *,
    outcomes: tuple[EvaluationWorkerOutcome, ...],
    ordered_paths: tuple[str, ...],
) -> tuple[FileEvaluation, ...]:
    evaluations_by_path: dict[str, FileEvaluation] = {}
    for outcome in outcomes:
        for file_evaluation in outcome.file_evaluations:
            evaluations_by_path[str(file_evaluation.path)] = file_evaluation
    ordered: list[FileEvaluation] = []
    for path in ordered_paths:
        found: FileEvaluation | None = evaluations_by_path.get(path)
        if found is not None:
            ordered.append(found)
    return tuple(ordered)


def _merged_dependencies(
    *, outcomes: tuple[EvaluationWorkerOutcome, ...]
) -> tuple[ProjectDependency, ...]:
    merged: list[ProjectDependency] = []
    for outcome in outcomes:
        merged.extend(outcome.dependencies)
    return tuple(merged)


def _contiguous_partitions(*, paths: tuple[str, ...], jobs: int) -> tuple[tuple[str, ...], ...]:
    worker_count: int = max(1, min(jobs, len(paths)))
    base_size, remainder = divmod(len(paths), worker_count)
    partitions: list[tuple[str, ...]] = []
    start: int = 0
    for index in range(worker_count):
        size: int = base_size + (1 if index < remainder else 0)
        partitions.append(paths[start : start + size])
        start += size
    return tuple(partition for partition in partitions if partition)


def _native_threads_per_worker(*, worker_count: int) -> int:
    return max(1, (os.cpu_count() or 1) // max(1, worker_count))


def _raise_worker_parse_failure(*, outcomes: tuple[EvaluationWorkerOutcome, ...]) -> None:
    for outcome in outcomes:
        if outcome.parse_failure is not None:
            raise ParseError(
                path=Path(outcome.parse_failure.path),
                message=outcome.parse_failure.message,
                line=outcome.parse_failure.line,
                column=outcome.parse_failure.column,
            )
