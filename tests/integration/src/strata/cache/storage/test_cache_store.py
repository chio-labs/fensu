"""Integration tests for persistent cache storage across store lifetimes."""

from __future__ import annotations

from pathlib import Path

import pytest

from strata.cache.storage.classes.cache_store import CacheStore
from strata.cache.storage.models import CacheRecord, CacheWrite
from tests.integration.src.strata.cache.storage._test_types import PersistentStoreTestCase
from tests.integration.src.strata.cache.storage.helpers import (
    read_batches_during_concurrent_writes,
    read_during_concurrent_writes,
    write_records_concurrently,
    write_while_database_blocked,
)


@pytest.mark.parametrize(
    "test_case",
    [
        PersistentStoreTestCase(
            description="independent stores share one persistent atomic record",
            relative_path="metadata.json",
            kind="metadata",
            writer_count=1,
            expected_payload_values=(7,),
            expected_temporary_count=0,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_written_record_when_opening_new_store_then_reads_persisted_value(
    tmp_path: Path,
    test_case: PersistentStoreTestCase,
) -> None:
    first_store: CacheStore = CacheStore(repo_root=tmp_path)
    expected_record: CacheRecord = CacheRecord(
        kind=test_case.kind,
        payload={"value": test_case.expected_payload_values[0]},
    )
    written: bool = first_store.write(
        relative_path=Path(test_case.relative_path),
        record=expected_record,
    )

    second_store: CacheStore = CacheStore(repo_root=tmp_path)
    loaded: CacheRecord | None = second_store.read(
        relative_path=Path(test_case.relative_path),
        expected_kind=test_case.kind,
    )

    assert written is True
    assert loaded == expected_record
    assert second_store.root.is_file()


@pytest.mark.parametrize(
    "test_case",
    [
        PersistentStoreTestCase(
            description="concurrent writers leave one complete readable record",
            relative_path="results/shared.json",
            kind="result",
            writer_count=8,
            expected_payload_values=tuple(range(8)),
            expected_temporary_count=0,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_concurrent_writers_when_publishing_same_entry_then_reader_sees_complete_record(
    tmp_path: Path,
    test_case: PersistentStoreTestCase,
) -> None:
    store: CacheStore = CacheStore(repo_root=tmp_path)

    writes: tuple[bool, ...] = write_records_concurrently(
        store=store,
        relative_path=Path(test_case.relative_path),
        kind=test_case.kind,
        values=test_case.expected_payload_values,
    )
    loaded: CacheRecord | None = store.read(
        relative_path=Path(test_case.relative_path),
        expected_kind=test_case.kind,
    )

    assert len(writes) == test_case.writer_count
    assert any(writes)
    assert loaded is not None
    assert isinstance(loaded.payload, dict)
    assert loaded.payload["value"] in test_case.expected_payload_values


@pytest.mark.parametrize(
    "test_case",
    [
        PersistentStoreTestCase(
            description="overlapping readers never observe partial concurrent writes",
            relative_path="results/observed.json",
            kind="result",
            writer_count=16,
            expected_payload_values=tuple(range(16)),
            expected_temporary_count=0,
            expected_miss_count=0,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_existing_entry_when_reading_during_writes_then_every_observation_is_complete(
    tmp_path: Path,
    test_case: PersistentStoreTestCase,
) -> None:
    store: CacheStore = CacheStore(repo_root=tmp_path)
    relative_path: Path = Path(test_case.relative_path)
    _ = store.write(
        relative_path=relative_path,
        record=CacheRecord(kind=test_case.kind, payload={"value": -1}),
    )

    observed: tuple[CacheRecord | None, ...] = read_during_concurrent_writes(
        store=store,
        relative_path=relative_path,
        kind=test_case.kind,
        values=test_case.expected_payload_values,
    )

    assert sum(record is None for record in observed) == test_case.expected_miss_count
    assert all(record is not None for record in observed)


@pytest.mark.parametrize(
    "test_case",
    [
        PersistentStoreTestCase(
            description="batch readers observe one complete transaction generation",
            relative_path="results/generation",
            kind="result",
            writer_count=8,
            expected_payload_values=tuple(range(8)),
            expected_temporary_count=0,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_multi_record_generations_when_reading_during_writes_then_never_observes_mixture(
    tmp_path: Path,
    test_case: PersistentStoreTestCase,
) -> None:
    store: CacheStore = CacheStore(repo_root=tmp_path)
    paths: tuple[Path, Path] = (
        Path(f"{test_case.relative_path}/first"),
        Path(f"{test_case.relative_path}/second"),
    )
    _ = store.write_batch(
        writes=tuple(
            CacheWrite(
                relative_path=path,
                record=CacheRecord(kind=test_case.kind, payload={"value": -1}),
            )
            for path in paths
        )
    )

    observed: tuple[tuple[CacheRecord | None, ...], ...] = read_batches_during_concurrent_writes(
        store=store,
        relative_paths=paths,
        kind=test_case.kind,
        values=test_case.expected_payload_values,
    )

    assert observed
    assert all(first is not None and second is not None for first, second in observed)
    assert all(first == second for first, second in observed)


@pytest.mark.parametrize(
    "test_case",
    [
        PersistentStoreTestCase(
            description="busy writer rejects publication without deleting committed database",
            relative_path="metadata.json",
            kind="metadata",
            writer_count=1,
            expected_payload_values=(7,),
            expected_temporary_count=0,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_busy_database_when_publishing_then_preserves_committed_state(
    tmp_path: Path,
    test_case: PersistentStoreTestCase,
) -> None:
    store: CacheStore = CacheStore(repo_root=tmp_path)
    previous: CacheRecord = CacheRecord(
        kind=test_case.kind,
        payload={"value": test_case.expected_payload_values[0]},
    )
    _ = store.write(relative_path=Path(test_case.relative_path), record=previous)
    written: bool = write_while_database_blocked(
        store=store,
        relative_path=Path(test_case.relative_path),
        record=CacheRecord(kind=test_case.kind, payload={"value": 8}),
    )
    loaded: CacheRecord | None = store.read(
        relative_path=Path(test_case.relative_path),
        expected_kind=test_case.kind,
    )

    assert written is False
    assert store.root.is_file()
    assert loaded == previous
