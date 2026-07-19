"""Evaluate one discovered tree across worker processes."""

from fensu.config.models import Config
from fensu.discovery.models import DiscoveredTree
from fensu.evaluation._helpers.parallel_evaluation import parallel_full_evaluation
from fensu.evaluation.models import EvaluationResult
from fensu.rules.authoring.models import CustomRuleRegistration, RuleSpec


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
