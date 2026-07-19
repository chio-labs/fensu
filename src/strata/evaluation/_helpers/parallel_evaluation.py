"""Run one full evaluation through repository-scale native parallelism."""

from __future__ import annotations

import os

from strata.config.models import Config
from strata.discovery.models import DiscoveredTree
from strata.evaluation.main.evaluate import evaluate
from strata.evaluation.models import EvaluationResult
from strata.instrumentation.constants import (
    EVALUATION_WORKER_PARTITION_OPERATION,
    OPERATION_COUNTERS,
)
from strata.rules.authoring.models import CustomRuleRegistration, RuleSpec

_MAXIMUM_AUTO_WORKERS: int = 8
_MINIMUM_PARALLEL_TARGETS: int = 200


def default_worker_count(*, target_count: int) -> int:
    """Return the measured-breakeven automatic native worker count."""

    if target_count < _MINIMUM_PARALLEL_TARGETS:
        return 1
    return max(1, min(_MAXIMUM_AUTO_WORKERS, os.cpu_count() or 1))


def parallel_full_evaluation(
    *,
    tree: DiscoveredTree,
    config: Config,
    ruleset: tuple[RuleSpec, ...],
    warning_rules: tuple[RuleSpec, ...] = (),
    custom_rule_registrations: tuple[CustomRuleRegistration, ...] = (),
    jobs: int,
) -> EvaluationResult:
    """Evaluate once while native indexed work uses the shared Rayon pool."""

    del jobs
    OPERATION_COUNTERS.record(operation=EVALUATION_WORKER_PARTITION_OPERATION)
    return evaluate(
        tree=tree,
        config=config,
        ruleset=ruleset,
        warning_rules=warning_rules,
        custom_rule_registrations=custom_rule_registrations,
    )
