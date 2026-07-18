"""Prepare Python-owned context for native per-file rule evaluation."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import cast

from strata.analysis.main.associate_rule_tests import associate_rule_tests
from strata.analysis.models import (
    EvaluateRuleCallFact,
    ProjectFunctionFact,
    RuleTestAssociationFact,
)
from strata.analysis.types import Analysis
from strata.config.main.resolve_threshold import resolve_threshold
from strata.config.models import Config, ThresholdResolution
from strata.discovery.main.position import position_facts
from strata.discovery.models import PositionFacts
from strata.discovery.types import ScopeName
from strata.evaluation.constants import INIT_MODULE_NAME
from strata.evaluation.models import EvaluationTarget, ThresholdOverrideUse
from strata.evaluation.types import (
    EvaluationProjectAnalysis,
    NativeCoreRuleRequest,
    NativeProjectQueryKind,
    NativeThresholdValues,
)
from strata.rules.authoring.models import CustomRuleRegistration
from strata.rules.authoring.types import Threshold

_threshold_by_code: dict[str, Threshold] = {
    "SFR601": Threshold.MAX_FILE_LINES,
    "SFR703": Threshold.MAX_SCRIPT_ENTRYPOINT_LINES,
    "SFS001": Threshold.MAX_STATEMENTS,
    "SFS002": Threshold.MAX_DISTINCT_CALLS,
    "SFS003": Threshold.MAX_LOCALS,
    "SFS010": Threshold.MAX_ARGUMENTS,
    "SFS011": Threshold.MAX_STATEMENTS_GLOBAL,
    "SFS120": Threshold.MAX_POSITIONAL_ARGS,
    "SFR707": Threshold.MIN_CUSTOM_RULE_TEST_CASES,
}
_main_only_threshold_codes: frozenset[str] = frozenset({"SFS001", "SFS002", "SFS003"})
_maximum_native_metric: int = 2**32 - 1
_native_naming_codes: frozenset[str] = frozenset({"SFN001", "SFN002", "SFN003", "SFN004"})


def prepare_native_rule_request(
    *,
    target: EvaluationTarget,
    program: object | None,
    codes: tuple[str, ...],
    config: Config,
    repo_root: Path,
    tooling_packages: tuple[str, ...],
    scope_roots: tuple[tuple[str, str], ...],
) -> tuple[NativeCoreRuleRequest | None, tuple[ThresholdOverrideUse, ...]]:
    """Build one raw native request and retain threshold override provenance."""

    if program is None:
        return None, ()
    position: PositionFacts = position_facts(target.scoped_file)
    repository_path: str = target.scoped_file.path.relative_to(repo_root).as_posix()
    thresholds: NativeThresholdValues = {}
    uses: list[ThresholdOverrideUse] = []
    for code in codes:
        threshold: Threshold | None = _threshold_by_code.get(code)
        if threshold is None or (
            code in _main_only_threshold_codes and not position.is_main_module
        ):
            continue
        resolution: ThresholdResolution = resolve_threshold(
            config=config,
            name=threshold,
            path=repository_path,
            role=position.role,
        )
        thresholds[threshold.value] = min(resolution.effective_value, _maximum_native_metric)
        if (
            resolution.matched_pattern is not None
            and resolution.reason is not None
            and resolution.override_order is not None
        ):
            uses.append(
                ThresholdOverrideUse(
                    threshold=resolution.threshold,
                    effective_value=resolution.effective_value,
                    matched_pattern=resolution.matched_pattern,
                    reason=resolution.reason,
                    override_order=resolution.override_order,
                    repository_path=resolution.repository_path,
                )
            )
    request: NativeCoreRuleRequest = (
        program,
        list(codes),
        target.scoped_file.scope.value,
        position.role,
        position.is_main_module,
        thresholds,
        repository_path,
        list(config.contracts.items()) if _native_naming_codes.intersection(codes) else [],
        list(position.relative_parts),
        position.is_entry_module,
        target.scoped_file.root.name,
        (
            list(tooling_packages),
            list(scope_roots),
            {},
            [
                (
                    registration.rule.code,
                    registration.module_name,
                    registration.function_name,
                    registration.source_path.relative_to(repo_root).as_posix(),
                    registration.declaration_line,
                    registration.declaration_column,
                )
                for registration in target.custom_rule_registrations
            ],
        ),
    )
    return request, tuple(uses)


def observe_native_rule_projects(
    *,
    native: ModuleType,
    requests: tuple[NativeCoreRuleRequest | None, ...],
    targets: tuple[EvaluationTarget, ...],
    project: EvaluationProjectAnalysis,
    repo_root: Path,
    scope_roots: tuple[tuple[str, str], ...],
) -> tuple[NativeCoreRuleRequest | None, ...]:
    """Fulfill native query plans through dependency-recording project APIs."""

    active: list[NativeCoreRuleRequest] = [request for request in requests if request is not None]
    plans: list[list[tuple[str, str, str, str]]] = native.plan_native_core_rule_queries(active)
    observed: list[NativeCoreRuleRequest | None] = []
    plan_index: int = 0
    for request, target in zip(requests, targets, strict=True):
        if request is None:
            observed.append(None)
            continue
        answers: dict[str, list[str]] = {}
        for key, kind, path_text, argument in plans[plan_index]:
            path: Path = repo_root / path_text
            if kind == NativeProjectQueryKind.EXISTS:
                answers[key] = [
                    _bool_text(project.exists(requester=target.scoped_file.path, path=path))
                ]
            elif kind == NativeProjectQueryKind.IS_FILE:
                answers[key] = [
                    _bool_text(project.is_file(requester=target.scoped_file.path, path=path))
                ]
            elif kind == NativeProjectQueryKind.IS_DIR:
                answers[key] = [
                    _bool_text(project.is_dir(requester=target.scoped_file.path, path=path))
                ]
            elif kind == NativeProjectQueryKind.DATACLASSES:
                answers[key] = [
                    fact.name
                    for fact in project.dataclasses(requester=target.scoped_file.path, path=path)
                ]
            elif kind == NativeProjectQueryKind.MODULE_FUNCTION:
                function: ProjectFunctionFact | None = project.module_function(
                    requester=target.scoped_file.path,
                    module_name=path_text,
                    function_name=argument,
                )
                answers[key] = (
                    []
                    if function is None
                    else ["meaningful" if function.meaningful_result else "empty"]
                )
            elif kind == NativeProjectQueryKind.PACKAGE_ANCHOR:
                answers[key] = [
                    _bool_text(
                        _is_package_anchor(
                            project=project,
                            requester=target.scoped_file.path,
                            package_dir=path,
                            reported_path=repo_root / argument,
                        )
                    )
                ]
            elif kind == NativeProjectQueryKind.CUSTOM_RULE_COVERAGE:
                answers[key] = _coverage_answers(
                    project=project,
                    requester=target.scoped_file.path,
                    registrations=target.custom_rule_registrations,
                    repo_root=repo_root,
                    scope_roots=scope_roots,
                )
        values: list[object] = list(request)
        project_context: tuple[object, ...] = request[11]
        values[11] = (*project_context[:2], answers, project_context[3])
        observed.append(cast(NativeCoreRuleRequest, tuple(values)))
        plan_index += 1
    return tuple(observed)


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


def _is_package_anchor(
    *,
    project: EvaluationProjectAnalysis,
    requester: Path,
    package_dir: Path,
    reported_path: Path,
) -> bool:
    init_path: Path = package_dir / "__init__.py"
    if project.exists(requester=requester, path=init_path):
        return reported_path == init_path
    modules: tuple[Path, ...] = tuple(
        sorted(project.glob(requester=requester, path=package_dir, pattern="*.py", recursive=True))
    )
    return bool(modules) and reported_path == modules[0]


def _coverage_answers(
    *,
    project: EvaluationProjectAnalysis,
    requester: Path,
    registrations: tuple[CustomRuleRegistration, ...],
    repo_root: Path,
    scope_roots: tuple[tuple[str, str], ...],
) -> list[str]:
    modules: dict[str, Analysis] = {}
    calls: list[EvaluateRuleCallFact] = []
    for scope, root_text in sorted(scope_roots):
        if scope != ScopeName.TEST:
            continue
        test_root: Path = repo_root / root_text
        for test_path in sorted(
            project.glob(requester=requester, path=test_root, pattern="*.py", recursive=True)
        ):
            analysis: Analysis | None = project.analysis(requester=requester, path=test_path)
            if analysis is None:
                continue
            modules[_module_name(path=test_path, import_root=test_root.parent)] = analysis
            calls.extend(analysis.facts.evaluate_rule_calls())
    source_analysis: Analysis | None = project.analysis(requester=requester, path=requester)
    if source_analysis is not None:
        for registration in registrations:
            modules[registration.module_name] = source_analysis
    associations: tuple[RuleTestAssociationFact, ...] = associate_rule_tests(
        calls=tuple(calls), modules=modules
    )
    answers: list[str] = []
    for registration in registrations:
        matching: tuple[RuleTestAssociationFact, ...] = tuple(
            item
            for item in associations
            if item.rule_reference.module_name == registration.module_name
            and item.rule_reference.symbol_name == registration.function_name
        )
        count: int = sum(item.provable_case_count for item in matching)
        dynamic: bool = any(item.unknown_case_count for item in matching)
        answers.append(f"{registration.rule.code}\0{count}\0{_bool_text(dynamic)}")
    return answers


def _module_name(*, path: Path, import_root: Path) -> str:
    parts: tuple[str, ...] = path.relative_to(import_root).with_suffix("").parts
    if parts and parts[-1] == INIT_MODULE_NAME:
        parts = parts[:-1]
    return ".".join(parts)
