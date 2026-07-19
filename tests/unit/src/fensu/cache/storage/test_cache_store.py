"""Tests for atomic repository-local cache storage."""

from __future__ import annotations

import os
import sqlite3
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
    CacheMutateBatchTestCase,
    CacheMutateNoneTestCase,
    CachePathTestCase,
    CacheStoreTestCase,
)
from tests.unit.src.fensu.cache.storage.helpers import (
    install_write_failure,
    recording_mutator,
    write_raw_cache_entry,
)


@pytest.mark.parametrize(
    "test_case",
    [
        CacheStoreTestCase(
            description="missing read does not create cache directories",
            relative_path="metadata.json",
            kind="metadata",
            payload={},
            expected_write=False,
            expected_record=None,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_missing_cache_when_reading_then_returns_miss_without_creating_storage(
    tmp_path: Path,
    test_case: CacheStoreTestCase,
) -> None:
    store: CacheStore = CacheStore(repo_root=tmp_path)

    record: CacheRecord | None = store.read(
        relative_path=Path(test_case.relative_path),
        expected_kind=test_case.kind,
    )

    assert record == test_case.expected_record
    assert store.root.exists() is test_case.expected_write


@pytest.mark.parametrize(
    "test_case",
    [
        CacheStoreTestCase(
            description="successful write publishes a readable complete record",
            relative_path="results/result.json",
            kind="result",
            payload={"faults": [], "path": "src/pkg/module.py"},
            expected_write=True,
            expected_record=CacheRecord(
                kind="result",
                payload={"faults": [], "path": "src/pkg/module.py"},
            ),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_cache_record_when_writing_then_atomically_round_trips(
    tmp_path: Path,
    test_case: CacheStoreTestCase,
) -> None:
    store: CacheStore = CacheStore(repo_root=tmp_path)
    record: CacheRecord = CacheRecord(kind=test_case.kind, payload=test_case.payload)

    written: bool = store.write(relative_path=Path(test_case.relative_path), record=record)
    loaded: CacheRecord | None = store.read(
        relative_path=Path(test_case.relative_path),
        expected_kind=test_case.kind,
    )

    assert written is test_case.expected_write
    assert loaded == test_case.expected_record
    assert store.root.name == "v4.db"
    with sqlite3.connect(store.root) as connection:
        journal_mode: tuple[str] | None = connection.execute("PRAGMA journal_mode").fetchone()
    assert journal_mode == ("wal",)


@pytest.mark.parametrize(
    "test_case",
    [
        CacheStoreTestCase(
            description="corrupted stored bytes become a cache miss",
            relative_path="index.json",
            kind="index",
            payload={},
            expected_write=False,
            expected_record=None,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_corrupted_entry_when_reading_then_returns_cache_miss(
    tmp_path: Path,
    test_case: CacheStoreTestCase,
) -> None:
    store: CacheStore = CacheStore(repo_root=tmp_path)
    write_raw_cache_entry(
        store=store,
        relative_path=test_case.relative_path,
        data=b"not-json",
    )

    loaded: CacheRecord | None = store.read(
        relative_path=Path(test_case.relative_path),
        expected_kind=test_case.kind,
    )

    assert loaded == test_case.expected_record


@pytest.mark.parametrize(
    "test_case",
    [
        CacheStoreTestCase(
            description="failed publication leaves no visible or temporary entry",
            relative_path="metadata.json",
            kind="metadata",
            payload={"global": "abc"},
            expected_write=False,
            expected_record=None,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_transaction_failure_when_writing_then_leaves_no_visible_entry(
    tmp_path: Path,
    test_case: CacheStoreTestCase,
) -> None:
    store: CacheStore = CacheStore(repo_root=tmp_path)
    install_write_failure(store=store)

    written: bool = store.write(
        relative_path=Path(test_case.relative_path),
        record=CacheRecord(kind=test_case.kind, payload=test_case.payload),
    )
    loaded: CacheRecord | None = store.read(
        relative_path=Path(test_case.relative_path),
        expected_kind=test_case.kind,
    )

    assert written is test_case.expected_write
    assert loaded == test_case.expected_record


@pytest.mark.parametrize(
    "test_case",
    [
        CacheStoreTestCase(
            description="failed replacement preserves the previous complete entry",
            relative_path="metadata.json",
            kind="metadata",
            payload={"global": "previous"},
            expected_write=False,
            expected_record=CacheRecord(kind="metadata", payload={"global": "previous"}),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_existing_entry_when_transaction_fails_then_preserves_previous_record(
    tmp_path: Path,
    test_case: CacheStoreTestCase,
) -> None:
    store: CacheStore = CacheStore(repo_root=tmp_path)
    previous: CacheRecord = CacheRecord(kind=test_case.kind, payload=test_case.payload)
    _ = store.write(relative_path=Path(test_case.relative_path), record=previous)
    install_write_failure(store=store)

    written: bool = store.write(
        relative_path=Path(test_case.relative_path),
        record=CacheRecord(kind=test_case.kind, payload={"global": "replacement"}),
    )
    loaded: CacheRecord | None = store.read(
        relative_path=Path(test_case.relative_path),
        expected_kind=test_case.kind,
    )

    assert written is test_case.expected_write
    assert loaded == test_case.expected_record


@pytest.mark.parametrize(
    "test_case",
    [
        CacheStoreTestCase(
            description="failure on later batch row rolls back every earlier row",
            relative_path="results/first",
            kind="result",
            payload={"value": 1},
            expected_write=False,
            expected_record=None,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_multi_record_batch_when_later_write_fails_then_rolls_back_transaction(
    tmp_path: Path,
    test_case: CacheStoreTestCase,
) -> None:
    store: CacheStore = CacheStore(repo_root=tmp_path)
    install_write_failure(store=store, failed_key="results/second")

    written: bool = store.write_batch(
        writes=(
            CacheWrite(
                relative_path=Path(test_case.relative_path),
                record=CacheRecord(kind=test_case.kind, payload=test_case.payload),
            ),
            CacheWrite(
                relative_path=Path("results/second"),
                record=CacheRecord(kind=test_case.kind, payload={"value": 2}),
            ),
        )
    )
    loaded: CacheRecord | None = store.read(
        relative_path=Path(test_case.relative_path),
        expected_kind=test_case.kind,
    )

    assert written is test_case.expected_write
    assert loaded == test_case.expected_record


@pytest.mark.parametrize(
    "test_case",
    [
        CachePathTestCase(
            description="parent traversal cannot escape the cache root",
            relative_path="../outside.json",
            expected_error_fragment="must stay below the cache root",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_escaping_cache_path_when_reading_then_raises_path_error(
    tmp_path: Path,
    test_case: CachePathTestCase,
) -> None:
    store: CacheStore = CacheStore(repo_root=tmp_path)

    with pytest.raises(CachePathError) as error:
        store.read(
            relative_path=Path(test_case.relative_path),
            expected_kind="metadata",
        )

    assert test_case.expected_error_fragment in str(error.value)


@pytest.mark.parametrize(
    "test_case",
    [
        CacheStoreTestCase(
            description="symlinked cache root cannot read or write outside repository",
            relative_path="metadata.json",
            kind="metadata",
            payload={"global": "abc"},
            expected_write=False,
            expected_record=None,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_symlinked_cache_root_when_accessing_then_refuses_external_target(
    tmp_path: Path,
    test_case: CacheStoreTestCase,
) -> None:
    external: Path = tmp_path / "external"
    external.mkdir()
    fensu_path: Path = tmp_path / ".fensu"
    fensu_path.symlink_to(external, target_is_directory=True)
    store: CacheStore = CacheStore(repo_root=tmp_path)

    written: bool = store.write(
        relative_path=Path(test_case.relative_path),
        record=CacheRecord(kind=test_case.kind, payload=test_case.payload),
    )
    loaded: CacheRecord | None = store.read(
        relative_path=Path(test_case.relative_path),
        expected_kind=test_case.kind,
    )

    assert written is test_case.expected_write
    assert loaded == test_case.expected_record
    assert not (external / "cache/v2.db").exists()


@pytest.mark.parametrize(
    "test_case",
    [
        CacheStoreTestCase(
            description="symlink loop is an unavailable cache rather than an error",
            relative_path="metadata.json",
            kind="metadata",
            payload={"global": "abc"},
            expected_write=False,
            expected_record=None,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_symlink_loop_when_accessing_cache_then_returns_miss(
    tmp_path: Path,
    test_case: CacheStoreTestCase,
) -> None:
    (tmp_path / ".fensu").symlink_to(".fensu", target_is_directory=True)
    store: CacheStore = CacheStore(repo_root=tmp_path)

    written: bool = store.write(
        relative_path=Path(test_case.relative_path),
        record=CacheRecord(kind=test_case.kind, payload=test_case.payload),
    )
    loaded: CacheRecord | None = store.read(
        relative_path=Path(test_case.relative_path),
        expected_kind=test_case.kind,
    )

    assert written is test_case.expected_write
    assert loaded == test_case.expected_record


@pytest.mark.parametrize(
    "test_case",
    [
        CacheStoreTestCase(
            description="FIFO cache entry is rejected without blocking",
            relative_path="metadata.json",
            kind="metadata",
            payload={},
            expected_write=False,
            expected_record=None,
        )
    ],
    ids=lambda case: case.description,
)
@pytest.mark.skipif(
    not hasattr(os, "mkfifo"),
    reason="FIFO test unavailable",
)
def test_given_fifo_database_when_reading_then_returns_miss_without_blocking(
    tmp_path: Path,
    test_case: CacheStoreTestCase,
) -> None:
    store: CacheStore = CacheStore(repo_root=tmp_path)
    store.root.parent.mkdir(parents=True)
    os.mkfifo(store.root)

    loaded: CacheRecord | None = store.read(
        relative_path=Path(test_case.relative_path),
        expected_kind=test_case.kind,
    )

    assert loaded == test_case.expected_record


@pytest.mark.parametrize(
    "test_case",
    [
        CacheMutateBatchTestCase(
            description="mutation reads merges publishes and sweeps in one transaction",
            retained_path="results/aa/keep.json",
            swept_path="results/aa/old.json",
            written_path="results/bb/new.json",
            unswept_path="metadata.json",
            expected_published=True,
            expected_retained_present=True,
            expected_swept_present=False,
            expected_written_present=True,
            expected_unswept_present=True,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_seeded_records_when_mutating_then_merges_publishes_and_sweeps(
    tmp_path: Path,
    test_case: CacheMutateBatchTestCase,
) -> None:
    store: CacheStore = CacheStore(repo_root=tmp_path)
    seeded: CacheRecord = CacheRecord(kind="file_result", payload={"path": "src/a.py"})
    metadata: CacheRecord = CacheRecord(kind="metadata", payload={})
    _ = store.write_batch(
        writes=(
            CacheWrite(relative_path=Path(test_case.retained_path), record=seeded),
            CacheWrite(relative_path=Path(test_case.swept_path), record=seeded),
            CacheWrite(relative_path=Path(test_case.unswept_path), record=metadata),
        )
    )
    written: CacheRecord = CacheRecord(kind="file_result", payload={"path": "src/b.py"})
    mutate, observed = recording_mutator(
        result=CacheMutation(
            writes=(CacheWrite(relative_path=Path(test_case.written_path), record=written),),
            swept_prefix=Path("results"),
            retained_paths=(Path(test_case.retained_path),),
        )
    )

    outcome: CacheMutationOutcome = store.mutate_batch(
        reads=(CacheRead(relative_path=Path(test_case.unswept_path), expected_kind="metadata"),),
        mutate=mutate,
    )

    assert outcome.published is test_case.expected_published
    assert observed == [(metadata,)]
    retained_read: CacheRecord | None = store.read(
        relative_path=Path(test_case.retained_path), expected_kind="file_result"
    )
    swept_read: CacheRecord | None = store.read(
        relative_path=Path(test_case.swept_path), expected_kind="file_result"
    )
    written_read: CacheRecord | None = store.read(
        relative_path=Path(test_case.written_path), expected_kind="file_result"
    )
    unswept_read: CacheRecord | None = store.read(
        relative_path=Path(test_case.unswept_path), expected_kind="metadata"
    )
    assert (retained_read is not None) is test_case.expected_retained_present
    assert (swept_read is not None) is test_case.expected_swept_present
    assert (written_read is not None) is test_case.expected_written_present
    assert (unswept_read is not None) is test_case.expected_unswept_present


@pytest.mark.parametrize(
    "test_case",
    [
        CacheMutateNoneTestCase(
            description="declined mutation preserves prior state without publication",
            seeded_path="results/aa/keep.json",
            expected_published=True,
            expected_seeded_record_read=True,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_declined_mutation_when_mutating_then_preserves_state(
    tmp_path: Path,
    test_case: CacheMutateNoneTestCase,
) -> None:
    store: CacheStore = CacheStore(repo_root=tmp_path)
    seeded: CacheRecord = CacheRecord(kind="file_result", payload={"path": "src/a.py"})
    _ = store.write_batch(
        writes=(CacheWrite(relative_path=Path(test_case.seeded_path), record=seeded),)
    )
    mutate, observed = recording_mutator(result=None)

    outcome: CacheMutationOutcome = store.mutate_batch(
        reads=(CacheRead(relative_path=Path(test_case.seeded_path), expected_kind="file_result"),),
        mutate=mutate,
    )

    assert outcome.published is test_case.expected_published
    assert outcome.mutation is None
    assert observed == [(seeded,)]
    loaded: CacheRecord | None = store.read(
        relative_path=Path(test_case.seeded_path), expected_kind="file_result"
    )
    assert (loaded is not None) is test_case.expected_seeded_record_read
