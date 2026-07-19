"""Evaluate registered native core rules for one prewarmed file chunk."""

from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path
from types import ModuleType
from typing import cast

from strata.analysis.constants import NATIVE_FACT_MODULE_NAME
from strata.config.exceptions import ConfigError
from strata.config.models import Config
from strata.evaluation._helpers.native_rules import (
    observe_native_rule_query_plans,
    prepare_native_execution_requests,
    prepare_native_project_plane,
    record_native_parses,
)
from strata.evaluation._helpers.parsing import parse_scoped_file, prewarm_native_programs
from strata.evaluation.models import (
    EvaluationTarget,
    NativeCoreRuleEvaluation,
)
from strata.evaluation.types import (
    EvaluationProjectAnalysis,
    NativeFaultRow,
    NativeFaultsByCode,
)
from strata.rules.authoring.models import Fault, RuleSpec
from strata.rules.roles.types import RoleCode


def evaluate_native_core_rules(
    *,
    targets: tuple[EvaluationTarget, ...],
    ruleset: tuple[RuleSpec, ...],
    warning_rules: tuple[RuleSpec, ...],
    config: Config,
    repo_root: Path,
    tooling_packages: tuple[str, ...],
    project: EvaluationProjectAnalysis,
    scope_roots: tuple[tuple[str, str], ...],
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
    snapshots, sources, prepared = prepare_native_execution_requests(
        targets=targets,
        codes_by_target=codes_by_target,
        config=config,
        repo_root=repo_root,
        tooling_packages=tooling_packages,
        scope_roots=scope_roots,
        project=project,
    )
    project_files, entrypoint_modules = prepare_native_project_plane(
        targets=targets,
        codes_by_target=codes_by_target,
        project=project,
        repo_root=repo_root,
        scope_roots=scope_roots,
    )
    record_native_parses(sources=sources)
    batch, plans, failures = native.plan_native_execution_batch(
        [request for request, _ in prepared],
        project_files,
        entrypoint_modules,
        sys.version_info[0],
        sys.version_info[1],
    )
    for index in failures:
        _ = parse_scoped_file(
            scoped_file=targets[index].scoped_file, source_snapshot=snapshots[index]
        )
    programs: list[object | None] = native.native_execution_programs(batch)
    prewarm_native_programs(
        project=project,
        scoped_files=tuple(target.scoped_file for target in targets),
        sources=sources,
        source_fingerprints=tuple(snapshot.fingerprint for snapshot in snapshots),
        programs=tuple(programs),
    )
    observations: list[dict[str, list[str]]] = observe_native_rule_query_plans(
        plans=plans,
        targets=targets,
        project=project,
        repo_root=repo_root,
        scope_roots=scope_roots,
    )
    try:
        batches: list[list[NativeFaultRow]] = native.evaluate_native_execution_batch(
            batch, observations
        )
    except ValueError as error:
        raise ConfigError(str(error)) from error
    return tuple(
        NativeCoreRuleEvaluation(
            faults_by_code=_faults_by_code(
                path=target.scoped_file.path,
                repo_root=repo_root,
                codes=codes,
                rows=tuple(rows),
                rules_by_code=rules_by_code,
            ),
            source_fingerprint=snapshot.fingerprint,
            source=source,
            program=cast(object, program),
            threshold_override_uses=uses,
        )
        for target, codes, rows, snapshot, source, program, (_, uses) in zip(
            targets,
            codes_by_target,
            batches,
            snapshots,
            sources,
            programs,
            prepared,
            strict=True,
        )
    )


def _target_native_codes(
    *,
    target: EvaluationTarget,
    rules: tuple[RuleSpec, ...],
    native_codes: frozenset[str],
) -> tuple[str, ...]:
    if not target.direct:
        return (
            (RoleCode.CUSTOM_RULE_TEST_COVERAGE,)
            if target.custom_rule_registrations
            and RoleCode.CUSTOM_RULE_TEST_COVERAGE in native_codes
            else ()
        )
    return tuple(
        rule.code
        for rule in rules
        if rule.code in native_codes
        and (target.applicable_rule_codes is None or rule.code in target.applicable_rule_codes)
    )


def _faults_by_code(
    *,
    path: Path,
    repo_root: Path,
    codes: tuple[str, ...],
    rows: tuple[NativeFaultRow, ...],
    rules_by_code: dict[str, RuleSpec],
) -> NativeFaultsByCode:
    grouped: dict[str, list[Fault]] = {code: [] for code in codes}
    for code, reported_path, line, column, message, remediation in rows:
        rule: RuleSpec = rules_by_code[code]
        grouped[code].append(
            Fault(
                code=code,
                path=path if reported_path is None else repo_root / reported_path,
                message=rule.message if message is None else message,
                line=line,
                column=column,
                remediation=rule.remediation if remediation is None else remediation,
            )
        )
    return {code: tuple(faults) for code, faults in grouped.items()}
