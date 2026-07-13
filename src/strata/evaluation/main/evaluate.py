"""Evaluate a ruleset over a discovered tree."""

from __future__ import annotations

from strata.config.models import Config
from strata.discovery.models import DiscoveredTree
from strata.evaluation._helpers.collection import collect_evaluation_result
from strata.evaluation._helpers.project_analysis import build_project_analysis
from strata.evaluation.main.build_targets import build_evaluation_targets
from strata.evaluation.main.evaluate_target import evaluate_target
from strata.evaluation.main.select_files import select_evaluation_files
from strata.evaluation.models import (
    EvaluationResult,
    EvaluationSelection,
    EvaluationTarget,
    FileEvaluation,
)
from strata.evaluation.types import EvaluationProjectAnalysis
from strata.rules.authoring.models import CustomRuleRegistration, RuleSpec


def evaluate(
    *,
    tree: DiscoveredTree,
    ruleset: tuple[RuleSpec, ...],
    warning_rules: tuple[RuleSpec, ...] = (),
    config: Config,
    custom_rule_registrations: tuple[CustomRuleRegistration, ...] = (),
) -> EvaluationResult:
    """Evaluate selected rules over discovered Python files."""

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
    for target in targets:
        file_result: FileEvaluation = evaluate_target(
            target=target,
            ruleset=ruleset,
            warning_rules=warning_rules,
            config=config,
            tree=tree,
            project=project,
        )
        file_evaluations.append(file_result)
    return collect_evaluation_result(
        file_evaluations=tuple(file_evaluations),
        dependencies=project.dependencies(),
        config=config,
        repo_root=tree.repo_root.path,
        evaluated_rule_codes=frozenset(rule.code for rule in (*ruleset, *warning_rules)),
        selection=selection,
    )
