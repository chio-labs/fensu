"""Evaluate one check invocation through the optional persistent cache."""

from __future__ import annotations

from pathlib import Path

from strata.cache.fingerprints.main.build_global import build_global_fingerprint
from strata.cache.fingerprints.models import GlobalFingerprintBuild
from strata.cache.results.main.evaluate import evaluate_with_cache
from strata.cache.results.models import CacheEvaluation
from strata.cli.models import CheckEvaluation
from strata.config.models import Config
from strata.discovery.models import DiscoveredTree
from strata.evaluation.main.evaluate import evaluate
from strata.evaluation.models import EvaluationResult
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
        build_global_fingerprint(
            config=config,
            ruleset=(*ruleset, *warning_rules),
            repo_root=project_dir,
            warnings_enabled=warn,
        )
        if config.cache.enabled
        else None
    )
    if fingerprint_build is None or fingerprint_build.fingerprint is None:
        result: EvaluationResult = evaluate(
            tree=tree,
            ruleset=ruleset,
            warning_rules=warning_rules,
            config=config,
            custom_rule_registrations=rule_selection.custom_registrations,
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
        )
    cached: CacheEvaluation = evaluate_with_cache(
        tree=tree,
        ruleset=ruleset,
        warning_rules=warning_rules,
        config=config,
        global_fingerprint=fingerprint_build.fingerprint,
        custom_rule_registrations=rule_selection.custom_registrations,
    )
    return CheckEvaluation(
        result=cached.result,
        stats=cached.stats,
        disabled_reason=fingerprint_build.disabled_reason,
        short_circuit=cached.short_circuit,
        surface_targets=cached.surface_targets,
        global_fingerprint=fingerprint_build.fingerprint,
    )
