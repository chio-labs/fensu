"""Collect merged per-file evaluations into one deterministic result."""

from __future__ import annotations

from pathlib import Path

from strata.analysis.models import ProjectDependency
from strata.config.models import Config
from strata.evaluation._helpers.collection import collect_evaluation_result
from strata.evaluation.models import EvaluationResult, EvaluationSelection, FileEvaluation


def collect_merged_evaluations(
    *,
    file_evaluations: tuple[FileEvaluation, ...],
    dependencies: tuple[ProjectDependency, ...],
    config: Config,
    repo_root: Path,
    evaluated_rule_codes: frozenset[str],
    selection: EvaluationSelection,
) -> EvaluationResult:
    """Combine partition outputs through the shared global collection contracts."""

    return collect_evaluation_result(
        file_evaluations=file_evaluations,
        dependencies=dependencies,
        config=config,
        repo_root=repo_root,
        evaluated_rule_codes=evaluated_rule_codes,
        selection=selection,
    )
