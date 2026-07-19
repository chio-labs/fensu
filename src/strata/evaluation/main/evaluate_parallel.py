"""Evaluate one discovered tree across worker processes."""

from strata.config.models import Config
from strata.discovery.models import DiscoveredTree
from strata.evaluation._helpers.parallel_evaluation import parallel_full_evaluation
from strata.evaluation.models import EvaluationResult
from strata.rules.authoring.models import CustomRuleRegistration, RuleSpec


def evaluate_parallel(
    *,
    tree: DiscoveredTree,
    config: Config,
    ruleset: tuple[RuleSpec, ...],
    warning_rules: tuple[RuleSpec, ...] = (),
    custom_rule_registrations: tuple[CustomRuleRegistration, ...] = (),
    jobs: int,
) -> EvaluationResult:
    """Evaluate every target across worker processes and collect deterministically."""

    return parallel_full_evaluation(
        tree=tree,
        config=config,
        ruleset=ruleset,
        warning_rules=warning_rules,
        custom_rule_registrations=custom_rule_registrations,
        jobs=jobs,
    )
