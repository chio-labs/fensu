"""Evaluate one discovered file through the uncached result boundary."""

from __future__ import annotations

from collections.abc import Mapping

from strata.config.models import Config
from strata.discovery.main.route import families_for_scope
from strata.discovery.models import DiscoveredTree, ScopedFile
from strata.evaluation._helpers.execution import execute_rule
from strata.evaluation._helpers.rule_exceptions import file_exception_scope, suppress_faults
from strata.evaluation.models import (
    FileEvaluation,
    FileExceptionScope,
    ParsedModule,
    RuleExceptionKey,
    ThresholdOverrideUse,
)
from strata.evaluation.types import EvaluationProjectAnalysis
from strata.rules.authoring.models import Fault, RuleSpec
from strata.rules.authoring.types import Family


def evaluate_file(
    *,
    scoped_file: ScopedFile,
    ruleset: tuple[RuleSpec, ...],
    warning_rules: tuple[RuleSpec, ...] = (),
    config: Config,
    tree: DiscoveredTree,
    project: EvaluationProjectAnalysis,
    file_cache_seed: Mapping[str, object] | None = None,
) -> FileEvaluation:
    """Return unrendered output and observed inputs for one source file."""

    parsed_module: ParsedModule = project.parsed_module(scoped_file)
    faults: list[Fault] = []
    warnings: list[Fault] = []
    applied_exceptions: set[RuleExceptionKey] = set()
    file_cache: dict[str, object] = dict(file_cache_seed or {})
    threshold_override_uses: list[ThresholdOverrideUse] = []
    applicable_families: frozenset[Family] = families_for_scope(scoped_file=scoped_file)
    exception_scope: FileExceptionScope | None = file_exception_scope(
        path=scoped_file.path,
        config=config,
        repo_root=tree.repo_root.path,
    )
    for tier_rules, tier_faults in ((ruleset, faults), (warning_rules, warnings)):
        for rule in tier_rules:
            if rule.family != Family.CUSTOM and rule.family not in applicable_families:
                continue
            rule_faults: list[Fault] = execute_rule(
                rule=rule,
                parsed_module=parsed_module,
                config=config,
                repo_root=tree.repo_root,
                layout=tree.layout,
                project=project,
                file_cache=file_cache,
                threshold_override_uses=threshold_override_uses,
            )
            if exception_scope is not None:
                retained, applied = suppress_faults(
                    faults=rule_faults,
                    parsed_module=parsed_module,
                    scope=exception_scope,
                )
                tier_faults.extend(retained)
                applied_exceptions.update(applied)
            else:
                tier_faults.extend(rule_faults)
    return FileEvaluation(
        path=scoped_file.path,
        source_fingerprint=parsed_module.source_fingerprint,
        faults=tuple(faults),
        warnings=tuple(warnings),
        applied_exception_keys=tuple(
            sorted(
                applied_exceptions,
                key=lambda item: (item.rule, item.path, item.symbol or ""),
            )
        ),
        dependencies=project.dependencies_for(requester=scoped_file.path),
        threshold_override_uses=tuple(sorted(set(threshold_override_uses), key=_override_use_key)),
    )


def _override_use_key(use: ThresholdOverrideUse) -> tuple[str, str, int, str, str, int]:
    return (
        use.repository_path,
        use.threshold.value,
        use.override_order,
        use.matched_pattern,
        use.reason,
        use.effective_value,
    )
