"""Helpers for persistent result-cache integration tests."""

from collections.abc import Callable
from pathlib import Path

import pytest

from strata.analysis.core.models import ProjectDependency
from strata.analysis.core.types import ProjectDependencyKind
from strata.cache.storage.classes.cache_store import CacheStore
from strata.cache.storage.models import CacheRecord
from strata.evaluation.core.models import FileEvaluation
from strata.rules.authoring.models import Fault


def file_evaluation(
    *,
    repo_root: Path,
    relative_path: str,
    fault_message: str = "missing annotation",
) -> FileEvaluation:
    """Return one deterministic runtime file evaluation."""

    path: Path = repo_root / relative_path
    return FileEvaluation(
        path=path,
        source_fingerprint="b" * 64,
        faults=(
            Fault(
                code="SFA001",
                path=path,
                message=fault_message,
                line=1,
                column=0,
            ),
        ),
        applied_exception_keys=(),
        dependencies=(
            ProjectDependency(
                requester=path,
                query_path=repo_root / "src/pkg/dependency.py",
                dependency=repo_root / "src/pkg/dependency.py",
                kind=ProjectDependencyKind.EXISTS,
                answer=False,
            ),
        ),
    )


def external_dependency_evaluation(*, repo_root: Path, relative_path: str) -> FileEvaluation:
    """Return a runtime result whose resolved dependency leaves the repository."""

    path: Path = repo_root / relative_path
    return FileEvaluation(
        path=path,
        source_fingerprint="b" * 64,
        faults=(),
        applied_exception_keys=(),
        dependencies=(
            ProjectDependency(
                requester=path,
                query_path=repo_root / "src/pkg/link.py",
                dependency=repo_root.parent / "external.py",
                kind=ProjectDependencyKind.SOURCE,
                answer="c" * 64,
            ),
        ),
    )


def install_cache_write_failure(
    *,
    monkeypatch: pytest.MonkeyPatch,
    failed_path: Path,
) -> None:
    """Fail one exact cache publication path while preserving other writes."""

    original: Callable[..., bool] = CacheStore.write

    def write(
        store: CacheStore,
        *,
        relative_path: Path,
        record: CacheRecord,
    ) -> bool:
        if relative_path == failed_path:
            return False
        return original(store, relative_path=relative_path, record=record)

    monkeypatch.setattr(CacheStore, "write", write)
