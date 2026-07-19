"""Evaluate one discovered file through the uncached result boundary."""

from __future__ import annotations

from collections.abc import Mapping

from fensu.config.models import Config
from fensu.discovery.main.route import families_for_scope
from fensu.discovery.models import DiscoveredTree, ScopedFile
from fensu.evaluation._helpers.execution import execute_rule
from fensu.evaluation._helpers.rule_exceptions import file_exception_scope, suppress_faults
from fensu.evaluation.models import (
    FileEvaluation,
    FileExceptionScope,
    NativeCoreRuleEvaluation,
    ParsedModule,
    RuleExceptionKey,
    ThresholdOverrideUse,
)
from fensu.evaluation.types import EvaluationProjectAnalysis
from fensu.rules.authoring.models import Fault, RuleSpec
from fensu.rules.authoring.types import Family


def evaluate_file(
    *,
    scoped_file: ScopedFile,
    ruleset: tuple[RuleSpec, ...],
    warning_rules: tuple[RuleSpec, ...] = (),
    config: Config,
    tree: DiscoveredTree,
    project: EvaluationProjectAnalysis,
    file_cache_seed: Mapping[str, object] | None = None,
    applicable_rule_codes: frozenset[str] | None = None,
    native_evaluation: NativeCoreRuleEvaluation | None = None,
) -> FileEvaluation:
    """Return unrendered output and observed inputs for one source file."""

    parsed_module: ParsedModule | None = None
    faults: list[Fault] = []
    warnings: list[Fault] = []
    applied_exceptions: set[RuleExceptionKey] = set()
    file_cache: dict[str, object] = dict(file_cache_seed or {})
    native_faults_by_code: Mapping[str, tuple[Fault, ...]] | None = (
        native_evaluation.faults_by_code if native_evaluation is not None else None
    )
    source_fingerprint: str | None = (
        native_evaluation.source_fingerprint if native_evaluation is not None else None
    )
    threshold_override_uses: list[ThresholdOverrideUse] = list(
        native_evaluation.threshold_override_uses if native_evaluation is not None else ()
    )
    applicable_families: frozenset[Family] = families_for_scope(scoped_file=scoped_file)
    exception_scope: FileExceptionScope | None = file_exception_scope(
        path=scoped_file.path,
        config=config,
        repo_root=tree.repo_root.path,
    )
    for tier_rules, tier_faults in ((ruleset, faults), (warning_rules, warnings)):
        for rule in tier_rules:
            if applicable_rule_codes is not None and rule.code not in applicable_rule_codes:
                continue
            if rule.family != Family.CUSTOM and rule.family not in applicable_families:
                continue
            if native_faults_by_code is not None and rule.code in native_faults_by_code:
                rule_faults: list[Fault] = list(native_faults_by_code[rule.code])
            else:
                if parsed_module is None:
                    parsed_module = project.parsed_module(scoped_file)
                rule_faults = execute_rule(
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
                if parsed_module is None:
                    parsed_module = project.parsed_module(scoped_file)
                retained, applied = suppress_faults(
                    faults=rule_faults,
                    parsed_module=parsed_module,
                    scope=exception_scope,
                )
                tier_faults.extend(retained)
                applied_exceptions.update(applied)
            else:
                tier_faults.extend(rule_faults)
    if source_fingerprint is None:
        if parsed_module is None:
            parsed_module = project.parsed_module(scoped_file)
        source_fingerprint = parsed_module.source_fingerprint
    return FileEvaluation(
        path=scoped_file.path,
        source_fingerprint=source_fingerprint,
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
