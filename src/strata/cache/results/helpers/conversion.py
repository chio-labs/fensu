"""Convert runtime file evaluations into backend-neutral cache records."""

from __future__ import annotations

from pathlib import Path

from strata.analysis.core.models import ProjectDependency
from strata.analysis.core.types import ProjectDependencyKind
from strata.cache.fingerprints.models import CacheFingerprint
from strata.cache.results.helpers.paths import relative_repository_path
from strata.cache.results.helpers.serialization import file_result_to_record
from strata.cache.results.models import (
    CachedFault,
    CachedFileResult,
    CachedRuleExceptionKey,
    DependencyObservation,
)
from strata.cache.results.types import DependencyAnswer
from strata.evaluation.core.models import FileEvaluation, RuleExceptionKey
from strata.rules.authoring.models import Fault


def build_cached_file_result(
    *,
    evaluation: FileEvaluation,
    repo_root: Path,
) -> CachedFileResult | None:
    """Return a cache-safe file result or None for unsupported path ownership."""

    path: str | None = relative_repository_path(path=evaluation.path, repo_root=repo_root)
    if path is None:
        return None
    faults: list[CachedFault] = []
    for fault in evaluation.faults:
        cached_fault: CachedFault | None = _cached_fault(
            fault=fault,
            requester_path=path,
            repo_root=repo_root,
        )
        if cached_fault is None:
            return None
        faults.append(cached_fault)
    exception_keys: list[CachedRuleExceptionKey] = []
    for key in evaluation.applied_exception_keys:
        cached_key: CachedRuleExceptionKey | None = _cached_exception_key(
            key=key,
            requester_path=path,
        )
        if cached_key is None:
            return None
        exception_keys.append(cached_key)
    dependencies: list[DependencyObservation] = []
    for dependency in evaluation.dependencies:
        observation: DependencyObservation | None = _dependency_observation(
            dependency=dependency,
            requester_path=path,
            repo_root=repo_root,
        )
        if observation is None:
            return None
        dependencies.append(observation)
    result: CachedFileResult = CachedFileResult(
        path=path,
        source_fingerprint=CacheFingerprint(evaluation.source_fingerprint),
        faults=tuple(faults),
        applied_exception_keys=tuple(exception_keys),
        dependencies=tuple(dependencies),
    )
    _ = file_result_to_record(result)
    return result


def restore_file_evaluation(*, result: CachedFileResult, repo_root: Path) -> FileEvaluation:
    """Restore one validated backend-neutral result to runtime evaluation models."""

    return FileEvaluation(
        path=repo_root / result.path,
        source_fingerprint=result.source_fingerprint.value,
        faults=tuple(
            Fault(
                code=fault.code,
                path=repo_root / fault.path,
                message=fault.message,
                line=fault.line,
                column=fault.column,
                remediation=fault.remediation,
            )
            for fault in result.faults
        ),
        applied_exception_keys=tuple(
            RuleExceptionKey(rule=key.rule, path=key.path, symbol=key.symbol)
            for key in result.applied_exception_keys
        ),
        dependencies=tuple(
            ProjectDependency(
                requester=repo_root / dependency.requester_path,
                query_path=repo_root / dependency.query_path,
                dependency=repo_root / dependency.dependency_path,
                kind=dependency.kind,
                answer=_restore_dependency_answer(answer=dependency.answer, repo_root=repo_root),
                pattern=dependency.pattern,
                recursive=dependency.recursive,
            )
            for dependency in result.dependencies
        ),
    )


def _cached_fault(
    *,
    fault: Fault,
    requester_path: str,
    repo_root: Path,
) -> CachedFault | None:
    path: str | None = relative_repository_path(path=fault.path, repo_root=repo_root)
    if path is None or path != requester_path:
        return None
    return CachedFault(
        code=fault.code,
        path=path,
        message=fault.message,
        line=fault.line,
        column=fault.column,
        remediation=fault.remediation,
    )


def _cached_exception_key(
    *,
    key: RuleExceptionKey,
    requester_path: str,
) -> CachedRuleExceptionKey | None:
    if key.path != requester_path:
        return None
    return CachedRuleExceptionKey(rule=key.rule, path=key.path, symbol=key.symbol)


def _dependency_observation(
    *,
    dependency: ProjectDependency,
    requester_path: str,
    repo_root: Path,
) -> DependencyObservation | None:
    requester: str | None = relative_repository_path(
        path=dependency.requester,
        repo_root=repo_root,
    )
    query_path: str | None = relative_repository_path(
        path=dependency.query_path,
        repo_root=repo_root,
        allow_root=True,
    )
    dependency_path: str | None = relative_repository_path(
        path=dependency.dependency,
        repo_root=repo_root,
        allow_root=True,
    )
    answer: DependencyAnswer | None = _dependency_answer(
        answer=dependency.answer,
        repo_root=repo_root,
    )
    try:
        kind: ProjectDependencyKind = ProjectDependencyKind(dependency.kind)
    except ValueError:
        return None
    if (
        requester is None
        or requester != requester_path
        or query_path is None
        or dependency_path is None
        or (answer is None and dependency.answer is not None)
    ):
        return None
    return DependencyObservation(
        requester_path=requester,
        query_path=query_path,
        dependency_path=dependency_path,
        kind=kind,
        answer=answer,
        pattern=dependency.pattern,
        recursive=dependency.recursive,
    )


def _dependency_answer(
    *,
    answer: None | bool | str | tuple[Path, ...],
    repo_root: Path,
) -> DependencyAnswer | None:
    if not isinstance(answer, tuple):
        return answer
    paths: list[str] = []
    for path in answer:
        relative_path: str | None = relative_repository_path(
            path=path,
            repo_root=repo_root,
            allow_root=True,
        )
        if relative_path is None:
            return None
        paths.append(relative_path)
    return tuple(paths)


def _restore_dependency_answer(
    *,
    answer: DependencyAnswer,
    repo_root: Path,
) -> None | bool | str | tuple[Path, ...]:
    if isinstance(answer, tuple):
        return tuple(repo_root / path for path in answer)
    return answer
