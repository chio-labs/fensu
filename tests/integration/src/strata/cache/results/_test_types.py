"""Test case types for persistent typed cache records."""

from __future__ import annotations

from dataclasses import dataclass

from strata.cache.results.models import CachedFileResult, CacheIndex


@dataclass(frozen=True)
class PersistentTypedResultTestCase:
    """One typed result and expected cross-store persistence behavior."""

    description: str
    relative_path: str
    result: CachedFileResult
    expected_write: bool
    expected_result: CachedFileResult


@dataclass(frozen=True)
class ResultCachePersistenceTestCase:
    """One published file evaluation and expected repository behavior."""

    description: str
    relative_path: str
    expected_index_entries: int
    expected_misses: int
    expected_writes: int
    expected_non_cacheable: int


@dataclass(frozen=True)
class ResultCacheMissTestCase:
    """One cache mismatch and expected safe miss."""

    description: str
    relative_path: str
    expected_result: CachedFileResult | None


@dataclass(frozen=True)
class ResultCachePublicationFailureTestCase:
    """One failed publication stage and expected unreachable result counts."""

    description: str
    relative_path: str
    failed_path: str
    expected_writes: int
    expected_index: CacheIndex | None
