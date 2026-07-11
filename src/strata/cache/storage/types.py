"""Persistent cache storage type declarations."""

from pathlib import Path
from typing import Protocol

from strata.cache.storage.models import CacheRecord


class CacheStorage(Protocol):
    """Minimal tagged persistent storage operations."""

    def read(self, *, relative_path: Path, expected_kind: str) -> CacheRecord | None:
        """Return one validated record or None for a miss."""
        ...

    def write(self, *, relative_path: Path, record: CacheRecord) -> bool:
        """Atomically publish one record when storage is available."""
        ...
