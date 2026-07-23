"""Prepare Python-owned context for native per-file rule evaluation."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from fensu.analysis.exceptions import PythonSourceParseError
from fensu.analysis.main.associate_rule_tests import associate_rule_tests
from fensu.analysis.main.decode_source import decode_python_source
from fensu.analysis.models import (
    EvaluateRuleCallFact,
    ProjectFunctionFact,
    RuleTestAssociationFact,
)
from fensu.analysis.types import Analysis
from fensu.config.main.resolve_threshold import resolve_threshold
from fensu.config.models import Config, ThresholdResolution
from fensu.discovery.main.position import position_facts
from fensu.discovery.models import PositionFacts
from fensu.discovery.types import ScopeName
from fensu.evaluation._helpers.parsing import parse_scoped_file, read_source_snapshot
from fensu.evaluation.constants import INIT_MODULE_NAME
from fensu.evaluation.models import EvaluationTarget, SourceSnapshot, ThresholdOverrideUse
from fensu.evaluation.types import (
    EvaluationProjectAnalysis,
    NativeExecutionRequest,
    NativeProjectFile,
    NativeProjectQueryKind,
    NativeRuleOptionValues,
    NativeThresholdValues,
)
from fensu.instrumentation.constants import NATIVE_PARSE_OPERATION, OPERATION_COUNTERS
from fensu.rules.authoring.models import CustomRuleRegistration
from fensu.rules.authoring.types import RuleOptionValue, Threshold
from fensu.rules.layers.types import LayerCode
from fensu.rules.roles.types import RoleCode

_thresholds_by_code: dict[str, tuple[Threshold, ...]] = {
    "FFR301": (Threshold.MAX_HELPERS_CONTAINER_MODULES, Threshold.MAX_ROLE_DEPTH),
    "FFR302": (Threshold.MAX_MAIN_CONTAINER_MODULES, Threshold.MAX_ROLE_DEPTH),
    "FFR308": (Threshold.MIN_SHARED_DOMAIN_PREFIX_PACKAGES,),
    "FFR601": (Threshold.MAX_FILE_LINES,),
    "FFR703": (Threshold.MAX_SCRIPT_ENTRYPOINT_LINES,),
    "FFS001": (Threshold.MAX_STATEMENTS,),
    "FFS002": (Threshold.MAX_DISTINCT_CALLS,),
    "FFS003": (Threshold.MAX_LOCALS,),
    "FFS010": (Threshold.MAX_ARGUMENTS,),
    "FFS011": (Threshold.MAX_STATEMENTS_GLOBAL,),
    "FFS120": (Threshold.MAX_POSITIONAL_ARGS,),
    "FFR707": (Threshold.MIN_CUSTOM_RULE_TEST_CASES,),
}
_main_only_threshold_codes: frozenset[str] = frozenset({"FFS001", "FFS002", "FFS003"})
_maximum_native_metric: int = 2**32 - 1
_native_naming_codes: frozenset[str] = frozenset({"FFN001", "FFN002", "FFN003", "FFN004"})
_true_text: str = "true"


def prepare_native_execution_request(
    *,
    target: EvaluationTarget,
    source: str,
    codes: tuple[str, ...],
    config: Config,
    repo_root: Path,
    tooling_packages: tuple[str, ...],
    scope_roots: tuple[tuple[str, str], ...],
    project: EvaluationProjectAnalysis,
) -> tuple[NativeExecutionRequest, tuple[ThresholdOverrideUse, ...]]:
    """Build one source-owned request for the opaque native execution batch."""

    position: PositionFacts = position_facts(target.scoped_file)
    repository_path: str = target.scoped_file.path.relative_to(repo_root).as_posix()
    shared_prefix_threshold_path: Path = _native_threshold_path(
        target=target,
        codes=codes,
        project=project,
    )
    thresholds: NativeThresholdValues = {}
    uses: list[ThresholdOverrideUse] = []
    selected_codes: frozenset[str] = frozenset(codes)
    for code, threshold_names in _thresholds_by_code.items():
        if code not in selected_codes or (
            code in _main_only_threshold_codes and not position.is_main_module
        ):
            continue
        threshold_repository_path: str = (
            (
                shared_prefix_threshold_path
                if code == RoleCode.SHARED_DOMAIN_PREFIX
                else target.scoped_file.path
            )
            .relative_to(repo_root)
            .as_posix()
        )
        for threshold in threshold_names:
            resolution: ThresholdResolution = resolve_threshold(
                config=config,
                name=threshold,
                path=threshold_repository_path,
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
    request: NativeExecutionRequest = (
        source,
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
            str(repo_root),
            _native_rule_options(config=config, codes=codes),
        ),
    )
    return request, tuple(uses)


def _native_rule_options(*, config: Config, codes: tuple[str, ...]) -> NativeRuleOptionValues:
    values: NativeRuleOptionValues = {}
    for code in codes:
        current: Mapping[str, RuleOptionValue] | None = config.rule_options.get(code)
        if current is None:
            continue
        values[code] = {
            name: json.dumps(value, ensure_ascii=True, separators=(",", ":"))
            for name, value in sorted(current.items())
        }
    return values


def record_native_parses(*, sources: tuple[str, ...]) -> None:
    """Record one native parse for every source crossing the batch boundary."""

    OPERATION_COUNTERS.record(operation=NATIVE_PARSE_OPERATION, amount=len(sources))


def prepare_native_execution_requests(
    *,
    targets: tuple[EvaluationTarget, ...],
    codes_by_target: tuple[tuple[str, ...], ...],
    config: Config,
    repo_root: Path,
    tooling_packages: tuple[str, ...],
    scope_roots: tuple[tuple[str, str], ...],
    project: EvaluationProjectAnalysis,
) -> tuple[
    tuple[SourceSnapshot, ...],
    tuple[str, ...],
    tuple[tuple[NativeExecutionRequest, tuple[ThresholdOverrideUse, ...]], ...],
]:
    """Read targets and build the aligned coarse native execution requests."""

    snapshots: tuple[SourceSnapshot, ...] = tuple(
        read_source_snapshot(path=target.scoped_file.path) for target in targets
    )
    decoded: list[str] = []
    for target, snapshot in zip(targets, snapshots, strict=True):
        try:
            source: str = decode_python_source(
                path=target.scoped_file.path,
                content=snapshot.content,
            )
        except PythonSourceParseError:
            source = parse_scoped_file(
                scoped_file=target.scoped_file,
                source_snapshot=snapshot,
            ).source
        decoded.append(source)
    sources: tuple[str, ...] = tuple(decoded)
    prepared: tuple[tuple[NativeExecutionRequest, tuple[ThresholdOverrideUse, ...]], ...] = tuple(
        prepare_native_execution_request(
            target=target,
            source=source,
            codes=codes,
            config=config,
            repo_root=repo_root,
            tooling_packages=tooling_packages,
            scope_roots=scope_roots,
            project=project,
        )
        for target, source, codes in zip(targets, sources, codes_by_target, strict=True)
    )
    return snapshots, sources, prepared


def prepare_native_project_plane(
    *,
    targets: tuple[EvaluationTarget, ...],
    codes_by_target: tuple[tuple[str, ...], ...],
    project: EvaluationProjectAnalysis,
    repo_root: Path,
    scope_roots: tuple[tuple[str, str], ...],
) -> tuple[list[NativeProjectFile], list[str]]:
    """Build one dependency-recorded project source plane for project-owned native rules."""

    requester: Path | None = next(
        (
            target.scoped_file.path
            for target, codes in zip(targets, codes_by_target, strict=True)
            if LayerCode.PUBLIC_MAIN_ENTRY_EXTERNAL_USE in codes
        ),
        None,
    )
    if requester is None:
        return [], []
    files: list[NativeProjectFile] = []
    for scope, root_text in scope_roots:
        if scope not in {ScopeName.ROOT, ScopeName.TOOLING}:
            continue
        root: Path = repo_root / root_text
        paths: set[Path] = set()
        for pattern in ("*.py", "*.pyi"):
            paths.update(
                project.glob(
                    requester=requester,
                    path=root,
                    pattern=pattern,
                    recursive=True,
                )
            )
        for path in sorted(paths):
            source: str | None = project.native_source(requester=requester, path=path)
            if source is None:
                continue
            module_parts: tuple[str, ...] = (*path.relative_to(root.parent).parts[:-1], path.stem)
            if module_parts[-1] == INIT_MODULE_NAME:
                module_parts = module_parts[:-1]
            files.append(
                (
                    path.relative_to(repo_root).as_posix(),
                    scope,
                    list(module_parts),
                    source,
                )
            )
    return files, list(project.entrypoint_modules(requester=requester))


def _native_threshold_path(
    *,
    target: EvaluationTarget,
    codes: tuple[str, ...],
    project: EvaluationProjectAnalysis,
) -> Path:
    if RoleCode.SHARED_DOMAIN_PREFIX not in codes:
        return target.scoped_file.path
    root: Path = target.scoped_file.root
    init_path: Path = root / f"{INIT_MODULE_NAME}.py"
    if project.is_file(requester=target.scoped_file.path, path=init_path):
        return init_path
    python_files: tuple[Path, ...] = tuple(
        sorted(
            project.glob(
                requester=target.scoped_file.path,
                path=root,
                pattern="*.py",
                recursive=True,
            )
        )
    )
    return python_files[0] if python_files else target.scoped_file.path


def observe_native_rule_query_plans(
    *,
    plans: list[list[tuple[str, str, str, str]]],
    targets: tuple[EvaluationTarget, ...],
    project: EvaluationProjectAnalysis,
    repo_root: Path,
    scope_roots: tuple[tuple[str, str], ...],
) -> list[dict[str, list[str]]]:
    """Fulfill one repository-scale native query plan through recorded project APIs."""

    return [
        _observe_query_plan(
            plan=plan,
            target=target,
            project=project,
            repo_root=repo_root,
            scope_roots=scope_roots,
        )
        for plan, target in zip(plans, targets, strict=True)
    ]


def _observe_query_plan(
    *,
    plan: list[tuple[str, str, str, str]],
    target: EvaluationTarget,
    project: EvaluationProjectAnalysis,
    repo_root: Path,
    scope_roots: tuple[tuple[str, str], ...],
) -> dict[str, list[str]]:
    answers: dict[str, list[str]] = {}
    for key, kind, path_text, argument in plan:
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
        elif kind == NativeProjectQueryKind.DIRECTORY_ENTRIES:
            answers[key] = [
                item.relative_to(repo_root).as_posix()
                for item in project.directory_entries(requester=target.scoped_file.path, path=path)
            ]
        elif kind == NativeProjectQueryKind.GLOB:
            pattern, recursive_text = argument.split("\0", maxsplit=1)
            answers[key] = [
                item.relative_to(repo_root).as_posix()
                for item in project.glob(
                    requester=target.scoped_file.path,
                    path=path,
                    pattern=pattern,
                    recursive=recursive_text == _true_text,
                )
            ]
        elif kind == NativeProjectQueryKind.PYTHON_ANCHOR:
            anchor: Path | None = project.python_anchor(
                requester=target.scoped_file.path,
                path=path,
            )
            answers[key] = [] if anchor is None else [anchor.relative_to(repo_root).as_posix()]
    return answers


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
