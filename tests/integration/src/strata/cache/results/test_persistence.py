"""Integration tests for typed cache records across store lifetimes."""

from __future__ import annotations

from pathlib import Path

import pytest

from strata.analysis.core.types import ProjectDependencyKind
from strata.cache.fingerprints.models import CacheFingerprint
from strata.cache.results.constants import CACHE_FILE_RESULT_KIND
from strata.cache.results.helpers.serialization import (
    file_result_from_record,
    file_result_to_record,
)
from strata.cache.results.models import CachedFault, CachedFileResult, DependencyObservation
from strata.cache.storage.classes.cache_store import CacheStore
from strata.cache.storage.constants import SECURE_CACHE_IO_SUPPORTED
from strata.cache.storage.models import CacheRecord
from tests.integration.src.strata.cache.results._test_types import PersistentTypedResultTestCase

pytestmark: object = pytest.mark.skipif(
    not SECURE_CACHE_IO_SUPPORTED,
    reason="secure descriptor I/O unavailable",
)

_SOURCE_FINGERPRINT: str = "d" * 64


@pytest.mark.parametrize(
    "test_case",
    [
        PersistentTypedResultTestCase(
            description="independent stores preserve a complete typed file result",
            relative_path="results/result.json",
            result=CachedFileResult(
                path="src/example.py",
                source_fingerprint=CacheFingerprint(_SOURCE_FINGERPRINT),
                faults=(
                    CachedFault(
                        code="SFX001",
                        path="src/example.py",
                        message="multiline docstring",
                        line=1,
                        column=0,
                    ),
                ),
                applied_exception_keys=(),
                dependencies=(
                    DependencyObservation(
                        requester_path="src/example.py",
                        query_path="src/missing.py",
                        dependency_path="src/missing.py",
                        kind=ProjectDependencyKind.EXISTS,
                        answer=False,
                    ),
                ),
            ),
            expected_write=True,
            expected_result=CachedFileResult(
                path="src/example.py",
                source_fingerprint=CacheFingerprint(_SOURCE_FINGERPRINT),
                faults=(
                    CachedFault(
                        code="SFX001",
                        path="src/example.py",
                        message="multiline docstring",
                        line=1,
                        column=0,
                    ),
                ),
                applied_exception_keys=(),
                dependencies=(
                    DependencyObservation(
                        requester_path="src/example.py",
                        query_path="src/missing.py",
                        dependency_path="src/missing.py",
                        kind=ProjectDependencyKind.EXISTS,
                        answer=False,
                    ),
                ),
            ),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_typed_result_when_reopening_store_then_preserves_complete_result(
    tmp_path: Path,
    test_case: PersistentTypedResultTestCase,
) -> None:
    first_store: CacheStore = CacheStore(repo_root=tmp_path)
    written: bool = first_store.write(
        relative_path=Path(test_case.relative_path),
        record=file_result_to_record(test_case.result),
    )

    second_store: CacheStore = CacheStore(repo_root=tmp_path)
    loaded: CacheRecord | None = second_store.read(
        relative_path=Path(test_case.relative_path),
        expected_kind=CACHE_FILE_RESULT_KIND,
    )
    assert loaded is not None
    decoded: CachedFileResult | None = file_result_from_record(loaded)

    assert written is test_case.expected_write
    assert decoded == test_case.expected_result
