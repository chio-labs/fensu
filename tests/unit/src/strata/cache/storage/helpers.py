"""Helpers for persistent cache storage unit tests."""

from __future__ import annotations

from pathlib import Path

from strata.cache.storage.classes.cache_store import CacheStore


def write_raw_cache_entry(*, store: CacheStore, relative_path: str, data: bytes) -> None:
    """Write unvalidated bytes directly into one cache entry."""

    path: Path = store.root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def fail_replace(
    source: str,
    destination: str,
    *,
    src_dir_fd: int | None = None,
    dst_dir_fd: int | None = None,
) -> None:
    """Simulate an interrupted atomic publication."""

    del source, destination, src_dir_fd, dst_dir_fd
    raise OSError("simulated replace failure")


def deeply_nested_cache_json(depth: int) -> bytes:
    """Return valid JSON nested beyond Python's safe decoder depth."""

    return (
        b'{"kind":"metadata","payload":' + (b"[" * depth) + (b"]" * depth) + b',"schema_version":1}'
    )
