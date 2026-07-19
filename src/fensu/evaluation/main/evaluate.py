"""Evaluate a ruleset over a discovered tree."""

from __future__ import annotations

from fensu.config.models import Config
from fensu.discovery.models import DiscoveredTree
from fensu.evaluation._helpers.collection import collect_evaluation_result
from fensu.evaluation.main._evaluate_partition import evaluate_partition
from fensu.evaluation.models import EvaluationResult, PartitionEvaluation
from fensu.rules.authoring.models import CustomRuleRegistration, RuleSpec


def evaluate(
    *,
    tree: DiscoveredTree,
    ruleset: tuple[RuleSpec, ...],
    warning_rules: tuple[RuleSpec, ...] = (),
    config: Config,
    custom_rule_registrations: tuple[CustomRuleRegistration, ...] = (),
) -> EvaluationResult:
    """Evaluate selected rules over discovered Python files."""

    partition_evaluation: PartitionEvaluation = evaluate_partition(
        tree=tree,
        ruleset=ruleset,
        warning_rules=warning_rules,
        config=config,
        custom_rule_registrations=custom_rule_registrations,
    )
    return collect_evaluation_result(
        file_evaluations=partition_evaluation.file_evaluations,
        dependencies=partition_evaluation.dependencies,
        config=config,
        repo_root=tree.repo_root.path,
        evaluated_rule_codes=frozenset(rule.code for rule in (*ruleset, *warning_rules)),
        selection=partition_evaluation.selection,
    )
