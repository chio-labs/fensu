"""Execute and merge one source-owned evaluation target."""

from __future__ import annotations

from strata.analysis.models import ProjectDependency
from strata.config.models import Config
from strata.discovery.models import DiscoveredTree
from strata.evaluation._helpers.file_evaluation import evaluate_file
from strata.evaluation.models import (
    EvaluationTarget,
    FileEvaluation,
    RuleExceptionKey,
    ThresholdOverrideUse,
)
from strata.evaluation.types import EvaluationProjectAnalysis
from strata.instrumentation.constants import FRESH_EVALUATION_OPERATION, OPERATION_COUNTERS
from strata.rules.authoring.constants import CUSTOM_RULE_REGISTRATIONS_CACHE_KEY
from strata.rules.authoring.models import Fault, RuleSpec
from strata.rules.roles.types import RoleCode


def evaluate_target(
    *,
    target: EvaluationTarget,
    ruleset: tuple[RuleSpec, ...],
    warning_rules: tuple[RuleSpec, ...],
    config: Config,
    tree: DiscoveredTree,
    project: EvaluationProjectAnalysis,
) -> FileEvaluation:
    """Evaluate normal rules and merge source-owned SFR707 supplemental output."""

    OPERATION_COUNTERS.record(operation=FRESH_EVALUATION_OPERATION)
    evaluations: list[FileEvaluation] = []
    if target.direct:
        evaluations.append(
            evaluate_file(
                scoped_file=target.scoped_file,
                ruleset=ruleset,
                warning_rules=warning_rules,
                config=config,
                tree=tree,
                project=project,
            )
        )
    if target.custom_rule_registrations:
        coverage_tier: tuple[RuleSpec, ...] = (
            warning_rules if target.custom_rule_coverage_warning else ruleset
        )
        coverage_rule: RuleSpec = next(
            rule for rule in coverage_tier if rule.code == RoleCode.CUSTOM_RULE_TEST_COVERAGE
        )
        evaluations.append(
            evaluate_file(
                scoped_file=target.scoped_file,
                ruleset=() if target.custom_rule_coverage_warning else (coverage_rule,),
                warning_rules=(coverage_rule,) if target.custom_rule_coverage_warning else (),
                config=config,
                tree=tree,
                project=project,
                file_cache_seed={
                    CUSTOM_RULE_REGISTRATIONS_CACHE_KEY: target.custom_rule_registrations
                },
            )
        )
    return _merge_file_evaluations(evaluations=tuple(evaluations))


def _merge_file_evaluations(*, evaluations: tuple[FileEvaluation, ...]) -> FileEvaluation:
    first: FileEvaluation = evaluations[0]
    faults: list[Fault] = []
    warnings: list[Fault] = []
    applied_exception_keys: set[RuleExceptionKey] = set()
    dependencies: dict[ProjectDependency, None] = {}
    threshold_override_uses: dict[ThresholdOverrideUse, None] = {}
    for evaluation in evaluations:
        faults.extend(evaluation.faults)
        warnings.extend(evaluation.warnings)
        applied_exception_keys.update(evaluation.applied_exception_keys)
        dependencies.update(dict.fromkeys(evaluation.dependencies))
        threshold_override_uses.update(dict.fromkeys(evaluation.threshold_override_uses))
    return FileEvaluation(
        path=first.path,
        source_fingerprint=first.source_fingerprint,
        faults=tuple(faults),
        warnings=tuple(warnings),
        applied_exception_keys=tuple(
            sorted(
                applied_exception_keys,
                key=lambda key: (key.rule, key.path, key.symbol or ""),
            )
        ),
        dependencies=tuple(dependencies),
        threshold_override_uses=tuple(threshold_override_uses),
    )
