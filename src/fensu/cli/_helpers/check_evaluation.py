"""Evaluate one check invocation through the optional persistent cache."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from fensu.cache.fingerprints.main.build_global import build_global_fingerprint
from fensu.cache.fingerprints.models import CacheFingerprint, GlobalFingerprintBuild
from fensu.cache.results.main.evaluate import evaluate_with_cache
from fensu.cache.results.models import CacheEvaluation
from fensu.cli.models import CheckEvaluation
from fensu.config.models import Config
from fensu.discovery.models import DiscoveredTree
from fensu.evaluation.main.evaluate_parallel import evaluate_parallel
from fensu.evaluation.main.resolve_worker_count import resolve_worker_count
from fensu.instrumentation.constants import (
    OPERATION_COUNTERS,
    PHASE_CACHE_EVALUATION_NANOSECONDS,
    PHASE_FULL_EVALUATION_NANOSECONDS,
    PHASE_GLOBAL_FINGERPRINT_NANOSECONDS,
)

if TYPE_CHECKING:
    from fensu.evaluation.models import EvaluationResult
    from fensu.rules.authoring.models import RuleSpec
    from fensu.rules.catalog.models import RuleSelection


def evaluated_check(
    *,
    tree: DiscoveredTree,
    config: Config,
    rule_selection: RuleSelection,
    project_dir: Path,
    warn: bool,
    jobs: int | None = None,
) -> CheckEvaluation:
    """Evaluate the tree with caching when available and return observability."""

    ruleset: tuple[RuleSpec, ...] = rule_selection.blocking
    warning_rules: tuple[RuleSpec, ...] = rule_selection.warnings if warn else ()
    resolved_jobs: int = (
        jobs if jobs is not None else resolve_worker_count(target_count=len(tree.files))
    )
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
            callback=lambda: _full_evaluation(
                tree=tree,
                config=config,
                rule_selection=rule_selection,
                warn=warn,
                jobs=resolved_jobs,
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
            jobs=resolved_jobs,
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


def _full_evaluation(
    *,
    tree: DiscoveredTree,
    config: Config,
    rule_selection: RuleSelection,
    warn: bool,
    jobs: int,
) -> EvaluationResult:
    if jobs > 1:
        return evaluate_parallel(
            tree=tree,
            config=config,
            ruleset=rule_selection.blocking,
            warning_rules=rule_selection.warnings if warn else (),
            custom_rule_registrations=rule_selection.custom_registrations,
            jobs=jobs,
        )
    from fensu.evaluation.main.evaluate import evaluate

    return evaluate(
        tree=tree,
        ruleset=rule_selection.blocking,
        warning_rules=rule_selection.warnings if warn else (),
        config=config,
        custom_rule_registrations=rule_selection.custom_registrations,
    )
