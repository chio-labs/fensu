"""Evaluate a discovered tree through validated persistent result caching."""

from fensu.cache.fingerprints.models import CacheFingerprint
from fensu.cache.results._helpers.evaluation import run_cached_evaluation
from fensu.cache.results.models import CacheEvaluation
from fensu.config.models import Config
from fensu.discovery.models import DiscoveredTree
from fensu.rules.authoring.models import CustomRuleRegistration, RuleSpec


def evaluate_with_cache(
    *,
    tree: DiscoveredTree,
    ruleset: tuple[RuleSpec, ...],
    warning_rules: tuple[RuleSpec, ...] = (),
    config: Config,
    global_fingerprint: CacheFingerprint,
    custom_rule_registrations: tuple[CustomRuleRegistration, ...] = (),
    allow_short_circuit: bool = True,
    jobs: int = 1,
) -> CacheEvaluation:
    """Return complete logical diagnostics and observable persistent-cache statistics."""

    return run_cached_evaluation(
        tree=tree,
        ruleset=ruleset,
        warning_rules=warning_rules,
        config=config,
        global_fingerprint=global_fingerprint,
        custom_rule_registrations=custom_rule_registrations,
        allow_short_circuit=allow_short_circuit,
        jobs=jobs,
    )
