"""Python adapter boundaries for native transactional cache storage."""

from __future__ import annotations

from pathlib import Path

import pytest

from fensu.cache.storage.classes.cache_store import CacheStore
from fensu.cache.storage.exceptions import CachePathError
from fensu.cache.storage.models import (
    CacheMutation,
    CacheMutationOutcome,
    CacheRead,
    CacheRecord,
    CacheWrite,
)
from tests.unit.src.fensu.cache.storage._test_types import (
    CacheMutationBoundaryTestCase,
    CachePathBoundaryTestCase,
    CacheStoreBoundaryTestCase,
)


@pytest.mark.parametrize(
    "test_case",
    [
        CacheStoreBoundaryTestCase(
            description="typed Python records round trip through native storage",
            relative_path="results/result.json",
            kind="result",
            payload={"faults": [], "path": "src/pkg/module.py"},
            expected_available=True,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_python_record_when_storing_then_crosses_native_boundary(
    tmp_path: Path,
    test_case: CacheStoreBoundaryTestCase,
) -> None:
    store: CacheStore = CacheStore(repo_root=tmp_path)
    expected: CacheRecord = CacheRecord(kind=test_case.kind, payload=test_case.payload)

    written: bool = store.write(relative_path=Path(test_case.relative_path), record=expected)
    loaded: CacheRecord | None = store.read(
        relative_path=Path(test_case.relative_path),
        expected_kind=test_case.kind,
    )

    assert written is test_case.expected_available
    assert (loaded == expected) is test_case.expected_available


@pytest.mark.parametrize(
    "test_case",
    [
        CachePathBoundaryTestCase(
            description="Python adapter rejects parent traversal before native storage",
            relative_path="../outside.json",
            expected_error_fragment="must stay below the cache root",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_escaping_path_when_storing_then_python_adapter_rejects_it(
    tmp_path: Path,
    test_case: CachePathBoundaryTestCase,
) -> None:
    store: CacheStore = CacheStore(repo_root=tmp_path)

    with pytest.raises(CachePathError) as error:
        store.read(relative_path=Path(test_case.relative_path), expected_kind="metadata")

    assert test_case.expected_error_fragment in str(error.value)


@pytest.mark.parametrize(
    "test_case",
    [
        CacheMutationBoundaryTestCase(
            description="Python mutation callback receives and returns typed records",
            seeded_path="metadata",
            written_path="results/new",
            expected_published=True,
            expected_written=True,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_python_mutator_when_publishing_then_crosses_native_transaction_boundary(
    tmp_path: Path,
    test_case: CacheMutationBoundaryTestCase,
) -> None:
    store: CacheStore = CacheStore(repo_root=tmp_path)
    seeded: CacheRecord = CacheRecord(kind="metadata", payload={"value": 1})
    _ = store.write(relative_path=Path(test_case.seeded_path), record=seeded)
    observed: list[tuple[CacheRecord | None, ...]] = []

    def mutate(records: tuple[CacheRecord | None, ...]) -> CacheMutation:
        observed.append(records)
        return CacheMutation(
            writes=(
                CacheWrite(
                    relative_path=Path(test_case.written_path),
                    record=CacheRecord(kind="result", payload={"value": 2}),
                ),
            )
        )

    outcome: CacheMutationOutcome = store.mutate_batch(
        reads=(CacheRead(relative_path=Path(test_case.seeded_path), expected_kind="metadata"),),
        mutate=mutate,
    )
    written: CacheRecord | None = store.read(
        relative_path=Path(test_case.written_path),
        expected_kind="result",
    )

    assert outcome.published is test_case.expected_published
    assert observed == [(seeded,)]
    assert (written is not None) is test_case.expected_written
