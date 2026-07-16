"""Execute and merge one source-owned evaluation target."""

from __future__ import annotations

from strata.config.models import Config
from strata.discovery.models import DiscoveredTree
from strata.evaluation._helpers.file_evaluation import evaluate_file
from strata.evaluation.main.merge_evaluations import merge_file_evaluations
from strata.evaluation.models import EvaluationTarget, FileEvaluation
from strata.evaluation.types import EvaluationProjectAnalysis
from strata.instrumentation.constants import FRESH_EVALUATION_OPERATION, OPERATION_COUNTERS
from strata.rules.authoring.constants import CUSTOM_RULE_REGISTRATIONS_CACHE_KEY
from strata.rules.authoring.models import RuleSpec
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
                applicable_rule_codes=target.applicable_rule_codes,
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
    return merge_file_evaluations(evaluations=tuple(evaluations))
