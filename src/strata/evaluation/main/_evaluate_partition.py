"""Evaluate one optional target partition without global fault collection."""

from __future__ import annotations

from strata.config.models import Config
from strata.discovery.models import DiscoveredTree
from strata.evaluation._helpers.parsing import prewarm_scoped_files
from strata.evaluation._helpers.project_analysis import build_project_analysis
from strata.evaluation.constants import PREWARM_CHUNK_SIZE
from strata.evaluation.main._evaluate_native_core_rules import evaluate_native_core_rules
from strata.evaluation.main.build_targets import build_evaluation_targets
from strata.evaluation.main.evaluate_target import evaluate_target
from strata.evaluation.main.select_files import select_evaluation_files
from strata.evaluation.models import (
    EvaluationSelection,
    EvaluationTarget,
    FileEvaluation,
    NativeCoreRuleEvaluation,
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
    for start in range(0, len(targets), PREWARM_CHUNK_SIZE):
        chunk: tuple[EvaluationTarget, ...] = targets[start : start + PREWARM_CHUNK_SIZE]
        native_programs: tuple[object | None, ...] = prewarm_scoped_files(
            project=project,
            scoped_files=tuple(target.scoped_file for target in chunk),
        )
        native_evaluations: tuple[NativeCoreRuleEvaluation, ...] = evaluate_native_core_rules(
            targets=chunk,
            programs=native_programs,
            ruleset=ruleset,
            warning_rules=warning_rules,
            config=config,
            repo_root=tree.repo_root.path,
            tooling_packages=tuple(source.package_name for source in tree.layout.tooling_sources),
        )
        for target, native_evaluation in zip(chunk, native_evaluations, strict=True):
            file_result: FileEvaluation = evaluate_target(
                target=target,
                ruleset=ruleset,
                warning_rules=warning_rules,
                config=config,
                tree=tree,
                project=project,
                native_evaluation=native_evaluation,
            )
            file_evaluations.append(file_result)
    return PartitionEvaluation(
        file_evaluations=tuple(file_evaluations),
        dependencies=project.dependencies(),
        selection=selection,
    )
