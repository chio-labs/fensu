"""Evaluate registered native core rules for one prewarmed file chunk."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from types import ModuleType

from strata.analysis.constants import NATIVE_FACT_MODULE_NAME
from strata.config.exceptions import ConfigError
from strata.config.models import Config
from strata.evaluation._helpers.native_rules import prepare_native_rule_request
from strata.evaluation.models import (
    EvaluationTarget,
    NativeCoreRuleEvaluation,
    ThresholdOverrideUse,
)
from strata.evaluation.types import NativeCoreRuleRequest, NativeFaultRow, NativeFaultsByCode
from strata.rules.authoring.models import Fault, RuleSpec


def evaluate_native_core_rules(
    *,
    targets: tuple[EvaluationTarget, ...],
    programs: tuple[object | None, ...],
    ruleset: tuple[RuleSpec, ...],
    warning_rules: tuple[RuleSpec, ...],
    config: Config,
    repo_root: Path,
    tooling_packages: tuple[str, ...],
) -> tuple[NativeCoreRuleEvaluation, ...]:
    """Return native faults grouped by rule code for each target."""

    native: ModuleType = import_module(NATIVE_FACT_MODULE_NAME)
    native_codes: frozenset[str] = frozenset(code for code, _ in native.native_rule_fact_families())
    rules_by_code: dict[str, RuleSpec] = {rule.code: rule for rule in (*ruleset, *warning_rules)}
    codes_by_target: tuple[tuple[str, ...], ...] = tuple(
        _target_native_codes(
            target=target,
            rules=(*ruleset, *warning_rules),
            native_codes=native_codes,
        )
        for target in targets
    )
    prepared: tuple[tuple[NativeCoreRuleRequest | None, tuple[ThresholdOverrideUse, ...]], ...] = (
        tuple(
            prepare_native_rule_request(
                target=target,
                program=program,
                codes=codes,
                config=config,
                repo_root=repo_root,
                tooling_packages=tooling_packages,
            )
            for target, program, codes in zip(targets, programs, codes_by_target, strict=True)
        )
    )
    try:
        batches: list[list[NativeFaultRow]] = native.evaluate_native_core_rules(
            [request for request, _ in prepared if request is not None]
        )
    except ValueError as error:
        raise ConfigError(str(error)) from error
    rows_by_target: list[list[NativeFaultRow]] = []
    batch_index: int = 0
    for request, _ in prepared:
        if request is None:
            rows_by_target.append([])
        else:
            rows_by_target.append(batches[batch_index])
            batch_index += 1
    return tuple(
        NativeCoreRuleEvaluation(
            faults_by_code=_faults_by_code(
                path=target.scoped_file.path,
                codes=codes,
                rows=tuple(rows),
                rules_by_code=rules_by_code,
            ),
            threshold_override_uses=uses,
        )
        for target, codes, rows, (_, uses) in zip(
            targets, codes_by_target, rows_by_target, prepared, strict=True
        )
    )


def _target_native_codes(
    *,
    target: EvaluationTarget,
    rules: tuple[RuleSpec, ...],
    native_codes: frozenset[str],
) -> tuple[str, ...]:
    if not target.direct:
        return ()
    return tuple(
        rule.code
        for rule in rules
        if rule.code in native_codes
        and (target.applicable_rule_codes is None or rule.code in target.applicable_rule_codes)
    )


def _faults_by_code(
    *,
    path: Path,
    codes: tuple[str, ...],
    rows: tuple[NativeFaultRow, ...],
    rules_by_code: dict[str, RuleSpec],
) -> NativeFaultsByCode:
    grouped: dict[str, list[Fault]] = {code: [] for code in codes}
    for code, line, column, message, remediation in rows:
        rule: RuleSpec = rules_by_code[code]
        grouped[code].append(
            Fault(
                code=code,
                path=path,
                message=rule.message if message is None else message,
                line=line,
                column=column,
                remediation=rule.remediation if remediation is None else remediation,
            )
        )
    return {code: tuple(faults) for code, faults in grouped.items()}
