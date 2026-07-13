"""Evaluate a discovered tree through validated persistent result caching."""

from strata.cache.fingerprints.models import CacheFingerprint
from strata.cache.results._helpers.evaluation import run_cached_evaluation
from strata.cache.results.models import CacheEvaluation
from strata.config.models import Config
from strata.discovery.models import DiscoveredTree
from strata.rules.authoring.models import RuleSpec


def evaluate_with_cache(
    *,
    tree: DiscoveredTree,
    ruleset: tuple[RuleSpec, ...],
    config: Config,
    global_fingerprint: CacheFingerprint,
) -> CacheEvaluation:
    """Return complete logical diagnostics and observable persistent-cache statistics."""

    return run_cached_evaluation(
        tree=tree,
        ruleset=ruleset,
        config=config,
        global_fingerprint=global_fingerprint,
    )
