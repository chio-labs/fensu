"""Persistent cache storage type declarations."""

from pathlib import Path
from typing import Protocol

from strata.cache.storage.models import CacheRead, CacheRecord, CacheWrite


class CacheStorage(Protocol):
    """Minimal tagged persistent storage operations."""

    def read(self, *, relative_path: Path, expected_kind: str) -> CacheRecord | None:
        """Return one validated record or None for a miss."""
        ...

    def read_batch(self, *, reads: tuple[CacheRead, ...]) -> tuple[CacheRecord | None, ...]:
        """Return validated records from one database snapshot."""
        ...

    def write(self, *, relative_path: Path, record: CacheRecord) -> bool:
        """Atomically publish one record when storage is available."""
        ...

    def write_batch(self, *, writes: tuple[CacheWrite, ...]) -> bool:
        """Atomically publish every record or preserve the previous state."""
        ...
