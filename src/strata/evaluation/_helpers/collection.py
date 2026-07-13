"""Fault collection and stable ordering helpers."""

from __future__ import annotations

from pathlib import Path

from strata.analysis.models import ProjectDependency
from strata.config.exceptions import ConfigError
from strata.config.models import Config
from strata.evaluation._helpers.rule_exceptions import (
    configured_exception_keys,
    stale_exception_error,
)
from strata.evaluation.models import (
    EvaluationResult,
    EvaluationSelection,
    FileEvaluation,
    RuleExceptionKey,
    ThresholdOverrideUse,
)
from strata.rules.authoring.models import Fault


def sort_faults(*, faults: list[Fault], repo_root: Path) -> tuple[Fault, ...]:
    """Return faults sorted by path, line, column, and code."""

    return tuple(
        sorted(faults, key=lambda fault: _fault_sort_key(fault=fault, repo_root=repo_root))
    )


def collect_evaluation_result(
    *,
    file_evaluations: tuple[FileEvaluation, ...],
    dependencies: tuple[ProjectDependency, ...],
    config: Config,
    repo_root: Path,
    evaluated_rule_codes: frozenset[str] | None = None,
    selection: EvaluationSelection | None = None,
) -> EvaluationResult:
    """Combine cached or fresh file outputs through the existing global contracts."""

    faults: list[Fault] = []
    warnings: list[Fault] = []
    applied_exceptions: set[RuleExceptionKey] = set()
    threshold_override_uses: set[ThresholdOverrideUse] = set()
    for file_evaluation in file_evaluations:
        faults.extend(file_evaluation.faults)
        warnings.extend(file_evaluation.warnings)
        applied_exceptions.update(file_evaluation.applied_exception_keys)
        threshold_override_uses.update(file_evaluation.threshold_override_uses)
    configured_exceptions: frozenset[RuleExceptionKey] = configured_exception_keys(config)
    if evaluated_rule_codes is not None:
        configured_exceptions = frozenset(
            key for key in configured_exceptions if key.rule in evaluated_rule_codes
        )
    if selection is not None and selection.filtered:
        target_paths: frozenset[str] = frozenset(
            scoped_file.path.relative_to(repo_root).as_posix() for scoped_file in selection.files
        )
        configured_exceptions = frozenset(
            key for key in configured_exceptions if key.path in target_paths
        )
    stale_error: ConfigError | None = stale_exception_error(
        configured=configured_exceptions,
        applied=frozenset(applied_exceptions),
    )
    if stale_error is not None:
        raise stale_error
    return EvaluationResult(
        faults=sort_faults(faults=faults, repo_root=repo_root),
        warnings=sort_faults(faults=warnings, repo_root=repo_root),
        applied_exception_count=len(applied_exceptions),
        dependencies=dependencies,
        file_evaluations=file_evaluations,
        threshold_override_uses=tuple(sorted(threshold_override_uses, key=_override_use_key)),
        selection=selection,
    )


def _fault_sort_key(*, fault: Fault, repo_root: Path) -> tuple[str, int, int, str]:
    try:
        relative_path: Path = fault.path.relative_to(repo_root)
    except ValueError:
        relative_path = fault.path
    line: int = -1 if fault.line is None else fault.line
    column: int = -1 if fault.column is None else fault.column
    return (relative_path.as_posix(), line, column, fault.code)


def _override_use_key(use: ThresholdOverrideUse) -> tuple[str, str, int, str, str, int]:
    return (
        use.repository_path,
        use.threshold.value,
        use.override_order,
        use.matched_pattern,
        use.reason,
        use.effective_value,
    )
