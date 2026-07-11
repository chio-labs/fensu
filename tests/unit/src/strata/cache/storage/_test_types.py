"""Test case types for persistent cache storage."""

from __future__ import annotations

from dataclasses import dataclass

from strata.cache.fingerprints.types import CanonicalValue
from strata.cache.storage.models import CacheRecord


@dataclass(frozen=True)
class CacheRecordRoundTripTestCase:
    """One cache record and its expected canonical serialization."""

    description: str
    kind: str
    payload: CanonicalValue
    expected_bytes: bytes


@dataclass(frozen=True)
class InvalidCacheRecordTestCase:
    """Unsupported cache bytes and the expected miss."""

    description: str
    data: bytes
    expected_kind: str
    expected_record: CacheRecord | None


@dataclass(frozen=True)
class InvalidCacheRecordWriteTestCase:
    """An invalid record and expected serialization error."""

    description: str
    kind: str
    expected_error_fragment: str


@dataclass(frozen=True)
class CacheStoreTestCase:
    """A cache entry and expected storage behavior."""

    description: str
    relative_path: str
    kind: str
    payload: CanonicalValue
    expected_write: bool
    expected_record: CacheRecord | None


@dataclass(frozen=True)
class CachePathTestCase:
    """An invalid cache path and expected error fragment."""

    description: str
    relative_path: str
    expected_error_fragment: str
