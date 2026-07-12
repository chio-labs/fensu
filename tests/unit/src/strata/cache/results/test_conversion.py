"""Tests for runtime evaluation to persistent result conversion."""

from __future__ import annotations

from pathlib import Path

import pytest

from strata.analysis.core.models import ProjectDependency
from strata.analysis.core.types import ProjectDependencyKind
from strata.cache.results.helpers.conversion import (
    build_cached_file_result,
    restore_file_evaluation,
)
from strata.cache.results.models import CachedFileResult
from strata.evaluation.core.models import FileEvaluation, RuleExceptionKey
from strata.rules.authoring.models import Fault
from tests.unit.src.strata.cache.results._test_types import (
    FileResultConversionTestCase,
    NonCacheableConversionTestCase,
)

_SOURCE_FINGERPRINT: str = "a" * 64


@pytest.mark.parametrize(
    "test_case",
    [
        FileResultConversionTestCase(
            description="runtime result converts without reading or reordering observations",
            relative_path="src/pkg/models.py",
            source_fingerprint=_SOURCE_FINGERPRINT,
            expected_fault_codes=("SFA001",),
            expected_dependency_answers=(False, ("src/pkg/b.py", "src/pkg/a.py")),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_runtime_file_result_when_converting_then_returns_cache_safe_record(
    tmp_path: Path,
    test_case: FileResultConversionTestCase,
) -> None:
    path: Path = tmp_path / test_case.relative_path
    evaluation: FileEvaluation = FileEvaluation(
        path=path,
        source_fingerprint=test_case.source_fingerprint,
        faults=(
            Fault(
                code="SFA001",
                path=path,
                message="missing annotation",
                line=1,
                column=None,
            ),
        ),
        applied_exception_keys=(
            RuleExceptionKey(rule="SFA001", path=test_case.relative_path, symbol="build"),
        ),
        dependencies=(
            ProjectDependency(
                requester=path,
                query_path=tmp_path / "src/pkg/missing.py",
                dependency=tmp_path / "src/pkg/missing.py",
                kind=ProjectDependencyKind.EXISTS,
                answer=False,
            ),
            ProjectDependency(
                requester=path,
                query_path=tmp_path / "src/pkg",
                dependency=tmp_path / "src/pkg",
                kind=ProjectDependencyKind.DIRECTORY_ENTRIES,
                answer=(tmp_path / "src/pkg/b.py", tmp_path / "src/pkg/a.py"),
            ),
        ),
    )

    result: CachedFileResult | None = build_cached_file_result(
        evaluation=evaluation,
        repo_root=tmp_path,
    )

    assert result is not None
    assert tuple(fault.code for fault in result.faults) == test_case.expected_fault_codes
    assert (
        tuple(item.answer for item in result.dependencies) == test_case.expected_dependency_answers
    )
    assert result.path == test_case.relative_path
    assert restore_file_evaluation(result=result, repo_root=tmp_path) == evaluation


@pytest.mark.parametrize(
    "test_case",
    [
        NonCacheableConversionTestCase(
            description="resolved dependency outside repository is non-cacheable",
            relative_path="src/pkg/models.py",
            expected_result=None,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_external_dependency_when_converting_then_returns_non_cacheable(
    tmp_path: Path,
    test_case: NonCacheableConversionTestCase,
) -> None:
    path: Path = tmp_path / test_case.relative_path
    path.parent.mkdir(parents=True)
    external: Path = tmp_path.parent / f"{tmp_path.name}-external.py"
    external.write_text("value: int = 1\n", encoding="utf-8")
    link: Path = tmp_path / "src/pkg/link.py"
    link.symlink_to(external)
    evaluation: FileEvaluation = FileEvaluation(
        path=path,
        source_fingerprint=_SOURCE_FINGERPRINT,
        faults=(),
        applied_exception_keys=(),
        dependencies=(
            ProjectDependency(
                requester=path,
                query_path=link,
                dependency=link.resolve(),
                kind=ProjectDependencyKind.SOURCE,
                answer=_SOURCE_FINGERPRINT,
            ),
        ),
    )

    result: CachedFileResult | None = build_cached_file_result(
        evaluation=evaluation,
        repo_root=tmp_path,
    )

    assert result == test_case.expected_result


@pytest.mark.parametrize(
    "test_case",
    [
        NonCacheableConversionTestCase(
            description="fault owned by another file is non-cacheable",
            relative_path="src/pkg/models.py",
            expected_result=None,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_cross_file_fault_when_converting_then_returns_non_cacheable(
    tmp_path: Path,
    test_case: NonCacheableConversionTestCase,
) -> None:
    evaluation: FileEvaluation = FileEvaluation(
        path=tmp_path / test_case.relative_path,
        source_fingerprint=_SOURCE_FINGERPRINT,
        faults=(
            Fault(
                code="SFA001",
                path=tmp_path / "src/pkg/other.py",
                message="cross-file fault",
            ),
        ),
        applied_exception_keys=(),
        dependencies=(),
    )

    result: CachedFileResult | None = build_cached_file_result(
        evaluation=evaluation,
        repo_root=tmp_path,
    )

    assert result == test_case.expected_result
