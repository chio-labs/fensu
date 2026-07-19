"""Convert runtime evaluations at the native cache boundary."""

from pathlib import Path
from typing import cast

from fensu.analysis.models import ProjectDependency
from fensu.analysis.types import ProjectDependencyKind
from fensu.cache.fingerprints.models import CacheFingerprint
from fensu.cache.results._helpers.paths import relative_repository_path
from fensu.evaluation.models import FileEvaluation, RuleExceptionKey, ThresholdOverrideUse
from fensu.rules.authoring.models import Fault
from fensu.rules.authoring.types import Threshold


def native_evaluation_payload(
    *, evaluation: FileEvaluation, repo_root: Path
) -> dict[str, object] | None:
    """Return one unvalidated native-publication boundary value or None when unowned."""

    path: str | None = relative_repository_path(path=evaluation.path, repo_root=repo_root)
    if path is None:
        return None
    dependencies: list[dict[str, object]] = []
    for dependency in evaluation.dependencies:
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
        answer: object = dependency.answer
        if isinstance(dependency.answer, tuple):
            converted_paths: list[str] = []
            for answer_path in dependency.answer:
                converted: str | None = relative_repository_path(
                    path=answer_path,
                    repo_root=repo_root,
                    allow_root=True,
                )
                if converted is None:
                    return None
                converted_paths.append(converted)
            answer = converted_paths
        if requester != path or query_path is None or dependency_path is None:
            return None
        try:
            kind: ProjectDependencyKind = ProjectDependencyKind(dependency.kind)
        except ValueError:
            return None
        dependencies.append(
            {
                "answer": answer,
                "dependency_path": dependency_path,
                "kind": kind.value,
                "pattern": dependency.pattern,
                "query_path": query_path,
                "recursive": dependency.recursive,
                "requester_path": requester,
            }
        )
    return {
        "applied_exception_keys": [
            {"path": key.path, "rule": key.rule, "symbol": key.symbol}
            for key in evaluation.applied_exception_keys
        ],
        "dependencies": dependencies,
        "faults": [
            _native_fault_value(fault=fault, repo_root=repo_root) for fault in evaluation.faults
        ],
        "path": path,
        "source_fingerprint": evaluation.source_fingerprint,
        "threshold_override_uses": [
            {
                "effective_value": use.effective_value,
                "matched_pattern": use.matched_pattern,
                "override_order": use.override_order,
                "reason": use.reason,
                "repository_path": use.repository_path,
                "threshold": use.threshold.value,
            }
            for use in evaluation.threshold_override_uses
        ],
        "warnings": [
            _native_fault_value(fault=warning, repo_root=repo_root)
            for warning in evaluation.warnings
        ],
    }


def restore_native_evaluation(*, payload: dict[str, object], repo_root: Path) -> FileEvaluation:
    """Restore one Rust-validated file-result payload into public runtime models."""

    path: str = cast(str, payload["path"])
    return FileEvaluation(
        path=repo_root / path,
        source_fingerprint=cast(str, payload["source_fingerprint"]),
        faults=tuple(
            _native_fault(value=value, repo_root=repo_root)
            for value in cast(list[dict[str, object]], payload["faults"])
        ),
        warnings=tuple(
            _native_fault(value=value, repo_root=repo_root)
            for value in cast(list[dict[str, object]], payload["warnings"])
        ),
        applied_exception_keys=tuple(
            RuleExceptionKey(
                rule=cast(str, value["rule"]),
                path=cast(str, value["path"]),
                symbol=cast(str | None, value["symbol"]),
            )
            for value in cast(list[dict[str, object]], payload["applied_exception_keys"])
        ),
        dependencies=tuple(
            ProjectDependency(
                requester=repo_root / cast(str, value["requester_path"]),
                query_path=repo_root / cast(str, value["query_path"]),
                dependency=repo_root / cast(str, value["dependency_path"]),
                kind=ProjectDependencyKind(cast(str, value["kind"])),
                answer=_native_dependency_answer(value=value["answer"], repo_root=repo_root),
                pattern=cast(str | None, value["pattern"]),
                recursive=cast(bool, value["recursive"]),
            )
            for value in cast(list[dict[str, object]], payload["dependencies"])
        ),
        threshold_override_uses=tuple(
            ThresholdOverrideUse(
                threshold=Threshold(cast(str, value["threshold"])),
                effective_value=cast(int, value["effective_value"]),
                matched_pattern=cast(str, value["matched_pattern"]),
                reason=cast(str, value["reason"]),
                override_order=cast(int, value["override_order"]),
                repository_path=cast(str, value["repository_path"]),
            )
            for value in cast(list[dict[str, object]], payload["threshold_override_uses"])
        ),
    )


def restore_native_contribution(
    *,
    payload: dict[str, object],
    source_fingerprint: CacheFingerprint,
    repo_root: Path,
) -> FileEvaluation:
    """Restore one Rust-validated sparse collection contribution."""

    value: dict[str, object] = {
        **payload,
        "dependencies": [],
        "source_fingerprint": source_fingerprint.value,
    }
    return restore_native_evaluation(payload=value, repo_root=repo_root)


def _native_fault_value(*, fault: Fault, repo_root: Path) -> dict[str, object]:
    path: str | None = relative_repository_path(path=fault.path, repo_root=repo_root)
    return {
        "code": fault.code,
        "column": fault.column,
        "line": fault.line,
        "message": fault.message,
        "path": path,
        "remediation": fault.remediation,
    }


def _native_fault(*, value: dict[str, object], repo_root: Path) -> Fault:
    return Fault(
        code=cast(str, value["code"]),
        path=repo_root / cast(str, value["path"]),
        message=cast(str, value["message"]),
        line=cast(int | None, value["line"]),
        column=cast(int | None, value["column"]),
        remediation=cast(str | None, value["remediation"]),
    )


def _native_dependency_answer(
    *, value: object, repo_root: Path
) -> None | bool | str | tuple[Path, ...]:
    if isinstance(value, list):
        return tuple(repo_root / cast(str, path) for path in value)
    return cast(None | bool | str, value)
