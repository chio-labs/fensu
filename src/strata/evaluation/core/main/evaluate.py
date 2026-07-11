"""Evaluate a ruleset over a discovered tree."""

from __future__ import annotations

from strata.config.core.exceptions import ConfigError
from strata.config.core.models import Config
from strata.discovery.core.models import DiscoveredTree
from strata.evaluation.core.helpers.collection import sort_faults
from strata.evaluation.core.helpers.file_evaluation import evaluate_file
from strata.evaluation.core.helpers.project_analysis import build_project_analysis
from strata.evaluation.core.helpers.rule_exceptions import (
    configured_exception_keys,
    stale_exception_error,
)
from strata.evaluation.core.models import EvaluationResult, FileEvaluation, RuleExceptionKey
from strata.evaluation.core.types import EvaluationProjectAnalysis
from strata.rules.authoring.models import Fault, RuleSpec


def evaluate(
    *,
    tree: DiscoveredTree,
    ruleset: tuple[RuleSpec, ...],
    config: Config,
) -> EvaluationResult:
    """Evaluate selected rules over discovered Python files."""

    faults: list[Fault] = []
    applied_exceptions: set[RuleExceptionKey] = set()
    file_evaluations: list[FileEvaluation] = []
    project: EvaluationProjectAnalysis = build_project_analysis(tree=tree)
    for scoped_file in tree.files:
        file_result: FileEvaluation = evaluate_file(
            scoped_file=scoped_file,
            ruleset=ruleset,
            config=config,
            tree=tree,
            project=project,
        )
        file_evaluations.append(file_result)
        faults.extend(file_result.faults)
        applied_exceptions.update(file_result.applied_exception_keys)
    configured: frozenset[RuleExceptionKey] = configured_exception_keys(config)
    stale_error: ConfigError | None = stale_exception_error(
        configured=configured, applied=frozenset(applied_exceptions)
    )
    if stale_error is not None:
        raise stale_error
    return EvaluationResult(
        faults=sort_faults(faults=faults, repo_root=tree.repo_root.path),
        applied_exception_count=len(applied_exceptions),
        dependencies=project.dependencies(),
        file_evaluations=tuple(file_evaluations),
    )
