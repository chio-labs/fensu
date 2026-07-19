"""Execute and merge one source-owned evaluation target."""

from __future__ import annotations

from dataclasses import replace

from fensu.config.models import Config
from fensu.discovery.models import DiscoveredTree
from fensu.evaluation._helpers.file_evaluation import evaluate_file
from fensu.evaluation.main.merge_evaluations import merge_file_evaluations
from fensu.evaluation.models import (
    EvaluationTarget,
    FileEvaluation,
    NativeCoreRuleEvaluation,
    ThresholdOverrideUse,
)
from fensu.evaluation.types import EvaluationProjectAnalysis, NativeFaultsByCode
from fensu.instrumentation.constants import FRESH_EVALUATION_OPERATION, OPERATION_COUNTERS
from fensu.rules.authoring.constants import CUSTOM_RULE_REGISTRATIONS_CACHE_KEY
from fensu.rules.authoring.models import RuleSpec
from fensu.rules.authoring.types import Threshold
from fensu.rules.roles.types import RoleCode


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
    """Evaluate normal rules and merge source-owned FFR707 supplemental output."""

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
                native_evaluation=(
                    replace(
                        native_evaluation,
                        faults_by_code=direct_native_faults or {},
                        threshold_override_uses=direct_native_uses,
                    )
                    if native_evaluation is not None
                    else None
                ),
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
                native_evaluation=(
                    replace(
                        native_evaluation,
                        faults_by_code={
                            RoleCode.CUSTOM_RULE_TEST_COVERAGE: (
                                native_evaluation.faults_by_code.get(
                                    RoleCode.CUSTOM_RULE_TEST_COVERAGE, ()
                                )
                            )
                        },
                        threshold_override_uses=tuple(
                            use
                            for use in native_evaluation.threshold_override_uses
                            if use.threshold is Threshold.MIN_CUSTOM_RULE_TEST_CASES
                        ),
                    )
                    if native_evaluation is not None
                    else None
                ),
            )
        )
    return merge_file_evaluations(evaluations=tuple(evaluations))
