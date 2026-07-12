"""Test case types for persistent evaluation-result cache records."""

from __future__ import annotations

from dataclasses import dataclass

from strata.analysis.types import ProjectDependencyKind
from strata.cache.fingerprints.types import CanonicalValue
from strata.cache.results.models import (
    CachedFact,
    CachedFileResult,
    CacheIndex,
    CacheMetadata,
)
from strata.cache.results.types import DependencyAnswer


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


@dataclass(frozen=True)
class FileResultConversionTestCase:
    """Runtime file evaluation and expected cache-safe values."""

    description: str
    relative_path: str
    source_fingerprint: str
    expected_fault_codes: tuple[str, ...]
    expected_dependency_answers: tuple[DependencyAnswer, ...]


@dataclass(frozen=True)
class NonCacheableConversionTestCase:
    """Unsupported runtime ownership and expected non-cacheable result."""

    description: str
    relative_path: str
    expected_result: CachedFileResult | None


@dataclass(frozen=True)
class DependencyInvalidationTestCase:
    """One dependency mutation and expected current-state answers."""

    description: str
    expected_before: bool
    expected_after: bool


@dataclass(frozen=True)
class DependencyReuseTestCase:
    """Equivalent requester observations and expected filesystem query count."""

    description: str
    requester_paths: tuple[str, ...]
    expected_current: bool
    expected_observation_count: int


@dataclass(frozen=True)
class ScalarDependencyInvalidationTestCase:
    """One scalar query kind and expected mutation invalidation."""

    description: str
    kind: ProjectDependencyKind
    expected_before: bool
    expected_after: bool


@dataclass(frozen=True)
class GlobDependencyInvalidationTestCase:
    """One glob recursion mode and expected namespace invalidation."""

    description: str
    recursive: bool
    expected_before: bool
    expected_after: bool
