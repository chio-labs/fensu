"""Evaluate one check invocation through the optional persistent cache."""

from __future__ import annotations

from pathlib import Path

from strata.cache.fingerprints.main.build_global import build_global_fingerprint
from strata.cache.fingerprints.models import CacheFingerprint, GlobalFingerprintBuild
from strata.cache.results.main.evaluate import evaluate_with_cache
from strata.cache.results.models import CacheEvaluation
from strata.cli.models import CheckEvaluation
from strata.config.models import Config
from strata.discovery.models import DiscoveredTree
from strata.evaluation.main.evaluate import evaluate
from strata.evaluation.models import EvaluationResult
from strata.instrumentation.constants import (
    OPERATION_COUNTERS,
    PHASE_CACHE_EVALUATION_NANOSECONDS,
    PHASE_FULL_EVALUATION_NANOSECONDS,
    PHASE_GLOBAL_FINGERPRINT_NANOSECONDS,
)
from strata.rules.authoring.models import RuleSpec
from strata.rules.catalog.models import RuleSelection


def evaluated_check(
    *,
    tree: DiscoveredTree,
    config: Config,
    rule_selection: RuleSelection,
    project_dir: Path,
    warn: bool,
) -> CheckEvaluation:
    """Evaluate the tree with caching when available and return observability."""

    ruleset: tuple[RuleSpec, ...] = rule_selection.blocking
    warning_rules: tuple[RuleSpec, ...] = rule_selection.warnings if warn else ()
    fingerprint_build: GlobalFingerprintBuild | None = (
        OPERATION_COUNTERS.measure(
            operation=PHASE_GLOBAL_FINGERPRINT_NANOSECONDS,
            callback=lambda: build_global_fingerprint(
                config=config,
                ruleset=(*ruleset, *warning_rules),
                repo_root=project_dir,
                warnings_enabled=warn,
            ),
        )
        if config.cache.enabled
        else None
    )
    global_fingerprint: CacheFingerprint | None = (
        None if fingerprint_build is None else fingerprint_build.fingerprint
    )
    if fingerprint_build is None or global_fingerprint is None:
        result: EvaluationResult = OPERATION_COUNTERS.measure(
            operation=PHASE_FULL_EVALUATION_NANOSECONDS,
            callback=lambda: evaluate(
                tree=tree,
                ruleset=ruleset,
                warning_rules=warning_rules,
                config=config,
                custom_rule_registrations=rule_selection.custom_registrations,
            ),
        )
        return CheckEvaluation(
            result=result,
            stats=None,
            disabled_reason=(
                fingerprint_build.disabled_reason if fingerprint_build is not None else None
            ),
            short_circuit=None,
            surface_targets=None,
            global_fingerprint=None,
            surface_index_fingerprint=None,
        )
    cached: CacheEvaluation = OPERATION_COUNTERS.measure(
        operation=PHASE_CACHE_EVALUATION_NANOSECONDS,
        callback=lambda: evaluate_with_cache(
            tree=tree,
            ruleset=ruleset,
            warning_rules=warning_rules,
            config=config,
            global_fingerprint=global_fingerprint,
            custom_rule_registrations=rule_selection.custom_registrations,
        ),
    )
    return CheckEvaluation(
        result=cached.result,
        stats=cached.stats,
        disabled_reason=fingerprint_build.disabled_reason,
        short_circuit=cached.short_circuit,
        surface_targets=cached.surface_targets,
        global_fingerprint=global_fingerprint,
        surface_index_fingerprint=cached.surface_index_fingerprint,
    )
