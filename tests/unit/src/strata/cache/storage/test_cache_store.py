"""Tests for atomic repository-local cache storage."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from strata.cache.storage.classes import cache_store as cache_store_module
from strata.cache.storage.classes.cache_store import CacheStore
from strata.cache.storage.constants import SECURE_CACHE_IO_SUPPORTED
from strata.cache.storage.exceptions import CachePathError
from strata.cache.storage.models import CacheRecord
from tests.unit.src.strata.cache.storage._test_types import CachePathTestCase, CacheStoreTestCase
from tests.unit.src.strata.cache.storage.helpers import fail_replace, write_raw_cache_entry


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
@pytest.mark.skipif(not SECURE_CACHE_IO_SUPPORTED, reason="secure descriptor I/O unavailable")
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
    assert tuple(store.root.rglob("*.tmp")) == ()


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
def test_given_atomic_replace_failure_when_writing_then_cleans_temporary_entry(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: CacheStoreTestCase,
) -> None:
    store: CacheStore = CacheStore(repo_root=tmp_path)
    monkeypatch.setattr(cache_store_module.os, "replace", fail_replace)

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
    assert tuple(store.root.rglob("*.tmp")) == ()


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
@pytest.mark.skipif(not SECURE_CACHE_IO_SUPPORTED, reason="secure descriptor I/O unavailable")
def test_given_existing_entry_when_replacement_fails_then_preserves_previous_record(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: CacheStoreTestCase,
) -> None:
    store: CacheStore = CacheStore(repo_root=tmp_path)
    previous: CacheRecord = CacheRecord(kind=test_case.kind, payload=test_case.payload)
    _ = store.write(relative_path=Path(test_case.relative_path), record=previous)
    monkeypatch.setattr(cache_store_module.os, "replace", fail_replace)

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
    assert tuple(store.root.rglob("*.tmp")) == ()


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
    strata_path: Path = tmp_path / ".strata"
    strata_path.symlink_to(external, target_is_directory=True)
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
    assert not (external / "cache/v1" / test_case.relative_path).exists()


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
    (tmp_path / ".strata").symlink_to(".strata", target_is_directory=True)
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
    not SECURE_CACHE_IO_SUPPORTED or not hasattr(os, "mkfifo"),
    reason="secure FIFO test unavailable",
)
def test_given_fifo_cache_entry_when_reading_then_returns_miss_without_blocking(
    tmp_path: Path,
    test_case: CacheStoreTestCase,
) -> None:
    store: CacheStore = CacheStore(repo_root=tmp_path)
    store.root.mkdir(parents=True)
    os.mkfifo(store.root / test_case.relative_path)

    loaded: CacheRecord | None = store.read(
        relative_path=Path(test_case.relative_path),
        expected_kind=test_case.kind,
    )

    assert loaded == test_case.expected_record
