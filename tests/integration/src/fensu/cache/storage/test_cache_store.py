"""Persistent native-cache behavior through the Python adapter boundary."""

from __future__ import annotations

from pathlib import Path

import pytest

from fensu.cache.storage.classes.cache_store import CacheStore
from fensu.cache.storage.models import CacheRecord
from tests.integration.src.fensu.cache.storage._test_types import PersistentStoreBoundaryTestCase
from tests.integration.src.fensu.cache.storage.helpers import write_records_concurrently


@pytest.mark.parametrize(
    "test_case",
    [
        PersistentStoreBoundaryTestCase(
            description="independent Python stores observe one native record",
            relative_path="metadata.json",
            kind="metadata",
            values=(7,),
            expected_available=True,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_written_record_when_opening_new_adapter_then_record_is_available(
    tmp_path: Path,
    test_case: PersistentStoreBoundaryTestCase,
) -> None:
    first: CacheStore = CacheStore(repo_root=tmp_path)
    expected: CacheRecord = CacheRecord(kind=test_case.kind, payload={"value": test_case.values[0]})
    _ = first.write(relative_path=Path(test_case.relative_path), record=expected)

    loaded: CacheRecord | None = CacheStore(repo_root=tmp_path).read(
        relative_path=Path(test_case.relative_path),
        expected_kind=test_case.kind,
    )

    assert (loaded == expected) is test_case.expected_available


@pytest.mark.parametrize(
    "test_case",
    [
        PersistentStoreBoundaryTestCase(
            description="concurrent Python adapters leave one complete native record",
            relative_path="results/shared.json",
            kind="result",
            values=tuple(range(8)),
            expected_available=True,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_concurrent_adapters_when_writing_then_complete_record_is_available(
    tmp_path: Path,
    test_case: PersistentStoreBoundaryTestCase,
) -> None:
    store: CacheStore = CacheStore(repo_root=tmp_path)

    outcomes: tuple[bool, ...] = write_records_concurrently(
        store=store,
        relative_path=Path(test_case.relative_path),
        kind=test_case.kind,
        values=test_case.values,
    )
    loaded: CacheRecord | None = store.read(
        relative_path=Path(test_case.relative_path),
        expected_kind=test_case.kind,
    )

    assert any(outcomes) is test_case.expected_available
    assert (loaded is not None) is test_case.expected_available
