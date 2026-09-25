"""Evaluate one optional target partition without global fault collection."""

from __future__ import annotations

from fensu.config.models import Config
from fensu.discovery.models import DiscoveredTree
from fensu.evaluation._helpers.project_analysis import build_project_analysis
from fensu.evaluation.main.build_targets import build_evaluation_targets
from fensu.evaluation.main.evaluate_project_rules import evaluate_project_rules
from fensu.evaluation.main.evaluate_target_chunk import evaluate_target_chunk
from fensu.evaluation.main.select_files import select_evaluation_files
from fensu.evaluation.models import (
    EvaluationSelection,
    EvaluationTarget,
    FileEvaluation,
    PartitionEvaluation,
    ProjectEvaluation,
)
from fensu.evaluation.types import EvaluationProjectAnalysis
from fensu.rules.authoring.models import CustomRuleRegistration, RuleSpec
from fensu.rules.authoring.types import RuleSubjectKind


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
    selection: EvaluationSelection = select_evaluation_files(
        tree=tree, config=config.evaluation, allow_empty=config.dead_code.enabled
    )
    project: EvaluationProjectAnalysis = build_project_analysis(tree=tree)
    file_rules: tuple[RuleSpec, ...] = tuple(
        rule for rule in ruleset if rule.subject_kind is not RuleSubjectKind.PROJECT
    )
    file_warnings: tuple[RuleSpec, ...] = tuple(
        rule for rule in warning_rules if rule.subject_kind is not RuleSubjectKind.PROJECT
    )
    project_rules: tuple[RuleSpec, ...] = tuple(
        rule for rule in ruleset if rule.subject_kind is RuleSubjectKind.PROJECT
    )
    project_warnings: tuple[RuleSpec, ...] = tuple(
        rule for rule in warning_rules if rule.subject_kind is RuleSubjectKind.PROJECT
    )
    targets: tuple[EvaluationTarget, ...] = (
        build_evaluation_targets(
            tree=tree,
            selection=selection,
            ruleset=file_rules,
            warning_rules=file_warnings,
            custom_rule_registrations=custom_rule_registrations,
        )
        if file_rules or file_warnings
        else ()
    )
    if partition is not None:
        targets = tuple(target for target in targets if str(target.scoped_file.path) in partition)
    file_evaluations.extend(
        evaluate_target_chunk(
            targets=targets,
            ruleset=file_rules,
            warning_rules=file_warnings,
            config=config,
            tree=tree,
            project=project,
        )
    )
    project_evaluation: ProjectEvaluation | None = evaluate_project_rules(
        ruleset=project_rules,
        warning_rules=project_warnings,
        config=config,
        tree=tree,
        analysis=project,
    )
    return PartitionEvaluation(
        file_evaluations=tuple(file_evaluations),
        dependencies=project.dependencies(),
        selection=selection,
        project_evaluation=project_evaluation,
    )
