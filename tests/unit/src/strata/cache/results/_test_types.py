"""Test case types for persistent evaluation-result cache records."""

from __future__ import annotations

from dataclasses import dataclass

from strata.cache.fingerprints.types import CanonicalValue
from strata.cache.results.models import (
    CachedFact,
    CachedFileResult,
    CacheIndex,
    CacheMetadata,
)


@dataclass(frozen=True)
class TypedRecordRoundTripTestCase:
    """One complete group of typed records and expected storage values."""

    description: str
    metadata: CacheMetadata
    index: CacheIndex
    file_result: CachedFileResult
    fact: CachedFact
    expected_kinds: tuple[str, ...]
    expected_dependency_payload: CanonicalValue


@dataclass(frozen=True)
class InvalidFileResultRecordTestCase:
    """One semantically invalid file-result payload and expected miss."""

    description: str
    payload: CanonicalValue
    expected_result: CachedFileResult | None


@dataclass(frozen=True)
class InvalidIndexWriteTestCase:
    """One invalid typed index and expected serialization failure."""

    description: str
    index: CacheIndex
    expected_error_fragment: str


@dataclass(frozen=True)
class InvalidDependencyRecordTestCase:
    """One invalid dependency payload and expected file-result miss."""

    description: str
    dependency: CanonicalValue
    expected_result: CachedFileResult | None
