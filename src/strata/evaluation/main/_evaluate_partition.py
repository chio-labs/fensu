"""Evaluate one optional target partition without global fault collection."""

from __future__ import annotations

from strata.config.models import Config
from strata.discovery.models import DiscoveredTree
from strata.evaluation._helpers.project_analysis import build_project_analysis
from strata.evaluation.main.build_targets import build_evaluation_targets
from strata.evaluation.main.evaluate_target_chunk import evaluate_target_chunk
from strata.evaluation.main.select_files import select_evaluation_files
from strata.evaluation.models import (
    EvaluationSelection,
    EvaluationTarget,
    FileEvaluation,
    PartitionEvaluation,
)
from strata.evaluation.types import EvaluationProjectAnalysis
from strata.rules.authoring.models import CustomRuleRegistration, RuleSpec


def evaluate_partition(
    *,
    tree: DiscoveredTree,
    ruleset: tuple[RuleSpec, ...],
    warning_rules: tuple[RuleSpec, ...] = (),
    config: Config,
    custom_rule_registrations: tuple[CustomRuleRegistration, ...] = (),
    partition: frozenset[str] | None = None,
) -> PartitionEvaluation:
    """Evaluate selected rules for every target, or only the named partition."""

    file_evaluations: list[FileEvaluation] = []
    selection: EvaluationSelection = select_evaluation_files(tree=tree, config=config.evaluation)
    project: EvaluationProjectAnalysis = build_project_analysis(tree=tree)
    targets: tuple[EvaluationTarget, ...] = build_evaluation_targets(
        tree=tree,
        selection=selection,
        ruleset=ruleset,
        warning_rules=warning_rules,
        custom_rule_registrations=custom_rule_registrations,
    )
    if partition is not None:
        targets = tuple(target for target in targets if str(target.scoped_file.path) in partition)
    file_evaluations.extend(
        evaluate_target_chunk(
            targets=targets,
            ruleset=ruleset,
            warning_rules=warning_rules,
            config=config,
            tree=tree,
            project=project,
        )
    )
    return PartitionEvaluation(
        file_evaluations=tuple(file_evaluations),
        dependencies=project.dependencies(),
        selection=selection,
    )
