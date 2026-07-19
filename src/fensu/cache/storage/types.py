"""Persistent cache storage type declarations."""

from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from fensu.cache.storage.models import (
    CacheMutation,
    CacheMutationOutcome,
    CacheRead,
    CacheRecord,
    CacheWrite,
)

type CacheMutator = Callable[[tuple[CacheRecord | None, ...]], CacheMutation | None]


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

    def mutate_batch(
        self,
        *,
        reads: tuple[CacheRead, ...],
        mutate: CacheMutator,
    ) -> CacheMutationOutcome:
        """Read, merge, publish, and sweep records in one exclusive transaction."""
        ...
