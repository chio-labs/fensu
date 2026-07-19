"""Typed adapter over native transactional repository cache storage."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from types import ModuleType
from typing import cast

from strata.cache.fingerprints.models import CacheFingerprint
from strata.cache.fingerprints.types import CanonicalValue
from strata.cache.storage._helpers.serialization import encode_cache_record
from strata.cache.storage.classes.native_cache_mutator import NativeCacheMutator
from strata.cache.storage.constants import CACHE_DATABASE_RELATIVE_PATH, PARENT_PATH_PART
from strata.cache.storage.exceptions import CachePathError
from strata.cache.storage.models import (
    CacheMutationOutcome,
    CacheRead,
    CacheRecord,
    CacheWrite,
    EncodedCacheWrite,
)
from strata.cache.storage.types import CacheMutator
from strata.instrumentation.constants import (
    CACHE_RECORD_BYTES_READ_OPERATION,
    CACHE_RECORD_BYTES_WRITTEN_OPERATION,
    CACHE_RECORD_DELETE_OPERATION,
    CACHE_RECORD_READ_OPERATION,
    CACHE_RECORD_SCAN_OPERATION,
    CACHE_RECORD_WRITE_OPERATION,
    OPERATION_COUNTERS,
)

type _NativeRecord = tuple[str, object, str]
type _NativeWrite = tuple[str, str, bytes, bool]
type _NativeMetrics = tuple[int, int, int, int, int, int]


class CacheStore:
    """Store canonical records in one native transactional database."""

    def __init__(self, *, repo_root: Path) -> None:
        """Bind storage without creating the cache database."""

        self._repo_root: Path = repo_root.resolve()
        self._database: Path = self._repo_root / CACHE_DATABASE_RELATIVE_PATH

    @property
    def root(self) -> Path:
        """Return the active cache database path."""

        return self._database

    def read(self, *, relative_path: Path, expected_kind: str) -> CacheRecord | None:
        """Return a validated record or None for any unavailable cache state."""

        return self.read_batch(
            reads=(CacheRead(relative_path=relative_path, expected_kind=expected_kind),)
        )[0]

    def read_batch(self, *, reads: tuple[CacheRead, ...]) -> tuple[CacheRecord | None, ...]:
        """Read and decode canonical records through one native database snapshot."""

        if not reads:
            return ()
        keyed_reads: tuple[tuple[str, str], ...] = tuple(
            (self.key(read.relative_path), read.expected_kind) for read in reads
        )
        try:
            native: ModuleType = import_module("strata._native")
            available, rows, metrics = native.cache_read_batch(
                self._repo_root,
                list(keyed_reads),
                _maximum_decoded_bytes(),
            )
        except (AttributeError, ImportError):
            return (None,) * len(reads)
        _record_metrics(metrics)
        if not available or len(rows) != len(reads):
            return (None,) * len(reads)
        return tuple(_record_from_native(row) for row in rows)

    def write(self, *, relative_path: Path, record: CacheRecord) -> bool:
        """Publish one record in a native transaction."""

        return self.write_batch(writes=(CacheWrite(relative_path=relative_path, record=record),))

    def write_batch(self, *, writes: tuple[CacheWrite, ...]) -> bool:
        """Commit every encoded record together or leave prior state unchanged."""

        if not writes:
            return True
        rows: tuple[_NativeWrite, ...] = self.encoded_rows(writes)
        try:
            native: ModuleType = import_module("strata._native")
            published, metrics = native.cache_write_batch(self._repo_root, list(rows))
        except (AttributeError, ImportError):
            return False
        _record_metrics(metrics)
        return published

    def mutate_batch(
        self,
        *,
        reads: tuple[CacheRead, ...],
        mutate: CacheMutator,
    ) -> CacheMutationOutcome:
        """Read, merge, publish, and sweep records in one native transaction."""

        keyed_reads: tuple[tuple[str, str], ...] = tuple(
            (self.key(read.relative_path), read.expected_kind) for read in reads
        )
        native_mutator: NativeCacheMutator = NativeCacheMutator(store=self, mutate=mutate)
        try:
            native: ModuleType = import_module("strata._native")
            published, applied, metrics = native.cache_mutate_batch(
                self._repo_root,
                list(keyed_reads),
                _maximum_decoded_bytes(),
                native_mutator,
            )
        except (AttributeError, ImportError):
            return CacheMutationOutcome(published=False, mutation=None)
        _record_metrics(metrics)
        return CacheMutationOutcome(
            published=published,
            mutation=native_mutator.selected if published and applied else None,
        )

    def encoded_rows(
        self,
        writes: tuple[CacheWrite | EncodedCacheWrite, ...],
    ) -> tuple[_NativeWrite, ...]:
        keys: set[str] = set()
        rows: list[_NativeWrite] = []
        for write in writes:
            key: str = self.key(write.relative_path)
            if key in keys:
                raise CachePathError(f"Cache publication contains duplicate key: {key}")
            keys.add(key)
            if isinstance(write, EncodedCacheWrite):
                rows.append((key, write.kind, write.encoded, write.insert_only))
                continue
            encoded: bytes = (
                write.encoded
                if write.encoded is not None
                else encode_cache_record(record=write.record)
            )
            rows.append((key, write.record.kind, encoded, False))
        return tuple(rows)

    def key(self, relative_path: Path) -> str:
        self._validate_relative_path(relative_path)
        return relative_path.as_posix()

    @staticmethod
    def record_from_native(row: _NativeRecord | None) -> CacheRecord | None:
        """Convert one validated native row to the typed storage model."""

        return _record_from_native(row)

    def _validate_relative_path(self, relative_path: Path) -> None:
        if (
            relative_path.is_absolute()
            or not relative_path.parts
            or PARENT_PATH_PART in relative_path.parts
        ):
            raise CachePathError(
                f"Cache entry path must stay below the cache root: {relative_path}"
            )


def _record_from_native(row: _NativeRecord | None) -> CacheRecord | None:
    if row is None:
        return None
    return CacheRecord(
        kind=row[0],
        payload=cast(CanonicalValue, row[1]),
        content_fingerprint=CacheFingerprint(value=row[2]),
    )


def _maximum_decoded_bytes() -> int:
    from strata.cache.storage._helpers.serialization import CACHE_RECORD_MAX_DECODED_BYTES

    return CACHE_RECORD_MAX_DECODED_BYTES


def _record_metrics(metrics: _NativeMetrics) -> None:
    operations: tuple[str, ...] = (
        CACHE_RECORD_READ_OPERATION,
        CACHE_RECORD_BYTES_READ_OPERATION,
        CACHE_RECORD_WRITE_OPERATION,
        CACHE_RECORD_BYTES_WRITTEN_OPERATION,
        CACHE_RECORD_SCAN_OPERATION,
        CACHE_RECORD_DELETE_OPERATION,
    )
    for operation, amount in zip(operations, metrics, strict=True):
        if amount:
            OPERATION_COUNTERS.record(operation=operation, amount=amount)
