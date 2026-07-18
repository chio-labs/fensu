"""Execute and merge one source-owned evaluation target."""

from __future__ import annotations

from strata.config.models import Config
from strata.discovery.models import DiscoveredTree
from strata.evaluation._helpers.file_evaluation import evaluate_file
from strata.evaluation.main.merge_evaluations import merge_file_evaluations
from strata.evaluation.models import (
    EvaluationTarget,
    FileEvaluation,
    NativeCoreRuleEvaluation,
    ThresholdOverrideUse,
)
from strata.evaluation.types import EvaluationProjectAnalysis, NativeFaultsByCode
from strata.instrumentation.constants import FRESH_EVALUATION_OPERATION, OPERATION_COUNTERS
from strata.rules.authoring.constants import CUSTOM_RULE_REGISTRATIONS_CACHE_KEY
from strata.rules.authoring.models import RuleSpec
from strata.rules.authoring.types import Threshold
from strata.rules.roles.types import RoleCode


def evaluate_target(
    *,
    target: EvaluationTarget,
    ruleset: tuple[RuleSpec, ...],
    warning_rules: tuple[RuleSpec, ...],
    config: Config,
    tree: DiscoveredTree,
    project: EvaluationProjectAnalysis,
    native_evaluation: NativeCoreRuleEvaluation | None = None,
) -> FileEvaluation:
    """Evaluate normal rules and merge source-owned SFR707 supplemental output."""

    OPERATION_COUNTERS.record(operation=FRESH_EVALUATION_OPERATION)
    evaluations: list[FileEvaluation] = []
    if target.direct:
        direct_native_faults: NativeFaultsByCode | None = (
            native_evaluation.faults_by_code if native_evaluation is not None else None
        )
        direct_native_uses: tuple[ThresholdOverrideUse, ...] = (
            native_evaluation.threshold_override_uses if native_evaluation is not None else ()
        )
        if target.custom_rule_registrations and direct_native_faults is not None:
            direct_native_faults = {
                code: faults
                for code, faults in direct_native_faults.items()
                if code != RoleCode.CUSTOM_RULE_TEST_COVERAGE
            }
            direct_native_uses = tuple(
                use
                for use in direct_native_uses
                if use.threshold is not Threshold.MIN_CUSTOM_RULE_TEST_CASES
            )
        evaluations.append(
            evaluate_file(
                scoped_file=target.scoped_file,
                ruleset=ruleset,
                warning_rules=warning_rules,
                config=config,
                tree=tree,
                project=project,
                applicable_rule_codes=target.applicable_rule_codes,
                native_faults_by_code=direct_native_faults,
                native_threshold_override_uses=direct_native_uses,
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
                native_faults_by_code=(
                    {
                        RoleCode.CUSTOM_RULE_TEST_COVERAGE: native_evaluation.faults_by_code.get(
                            RoleCode.CUSTOM_RULE_TEST_COVERAGE, ()
                        )
                    }
                    if native_evaluation is not None
                    else None
                ),
                native_threshold_override_uses=(
                    tuple(
                        use
                        for use in native_evaluation.threshold_override_uses
                        if use.threshold is Threshold.MIN_CUSTOM_RULE_TEST_CASES
                    )
                    if native_evaluation is not None
                    else ()
                ),
            )
        )
    return merge_file_evaluations(evaluations=tuple(evaluations))
