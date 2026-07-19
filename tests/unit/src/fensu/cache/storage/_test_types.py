"""Test case types for persistent cache storage."""

from __future__ import annotations

from dataclasses import dataclass

from fensu.cache.fingerprints.types import CanonicalValue
from fensu.cache.storage.models import CacheRecord


@dataclass(frozen=True)
class CacheRecordRoundTripTestCase:
    """One cache record and its expected canonical serialization."""

    description: str
    kind: str
    payload: CanonicalValue
    expected_bytes: bytes


@dataclass(frozen=True)
class CompressedCacheRecordTestCase:
    """One large canonical payload and compressed storage expectation."""

    description: str
    payload_size: int
    expected_prefix: bytes
    expected_smaller: bool


@dataclass(frozen=True)
class BoundedCompressedCacheRecordTestCase:
    """One compressed payload and maximum decoded-size expectation."""

    description: str
    decoded_limit: int
    payload_size: int
    expected_record: None


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


@dataclass(frozen=True)
class CacheMutateBatchTestCase:
    """One transactional mutation and its expected merged storage state."""

    description: str
    retained_path: str
    swept_path: str
    written_path: str
    unswept_path: str
    expected_published: bool
    expected_retained_present: bool
    expected_swept_present: bool
    expected_written_present: bool
    expected_unswept_present: bool


@dataclass(frozen=True)
class CacheMutateNoneTestCase:
    """A declined mutation and its expected untouched storage state."""

    description: str
    seeded_path: str
    expected_published: bool
    expected_seeded_record_read: bool
