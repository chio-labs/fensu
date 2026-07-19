"""Helpers for persistent cache storage unit tests."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from strata.cache.storage.classes.cache_store import CacheStore
from strata.cache.storage.models import CacheMutation, CacheRecord
from strata.cache.storage.types import CacheMutator


def recording_mutator(
    *,
    result: CacheMutation | None,
) -> tuple[CacheMutator, list[tuple[CacheRecord | None, ...]]]:
    """Return a mutator producing one fixed mutation while recording observed reads."""

    observed: list[tuple[CacheRecord | None, ...]] = []

    def mutate(records: tuple[CacheRecord | None, ...]) -> CacheMutation | None:
        observed.append(records)
        return result

    return mutate, observed


def write_raw_cache_entry(*, store: CacheStore, relative_path: str, data: bytes) -> None:
    """Write unvalidated bytes directly into one cache entry."""

    _ = store.write(
        relative_path=Path(relative_path),
        record=CacheRecord(kind="index", payload={}),
    )
    with sqlite3.connect(store.root) as connection:
        connection.execute("UPDATE records SET data = ? WHERE key = ?", (data, relative_path))


def install_write_failure(*, store: CacheStore, failed_key: str | None = None) -> None:
    """Install a database trigger that aborts every record update."""

    _ = store.write(
        relative_path=Path("setup"),
        record=CacheRecord(kind="setup", payload={}),
    )
    with sqlite3.connect(store.root) as connection:
        condition: str = {
            True: "",
            False: f" WHEN NEW.key = '{failed_key}'",
        }[failed_key is None]
        connection.execute(
            f"CREATE TRIGGER fail_writes BEFORE INSERT ON records{condition} "
            "BEGIN SELECT RAISE(ABORT, 'simulated write failure'); END"
        )


def deeply_nested_cache_json(depth: int) -> bytes:
    """Return valid JSON nested beyond Python's safe decoder depth."""

    return (
        b'{"kind":"metadata","payload":' + (b"[" * depth) + (b"]" * depth) + b',"schema_version":1}'
    )
