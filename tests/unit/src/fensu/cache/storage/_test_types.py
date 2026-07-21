"""Test-case types for Python-facing native cache adapters."""

from __future__ import annotations

from dataclasses import dataclass

from fensu.cache.fingerprints.types import CanonicalValue


@dataclass(frozen=True)
class SerializationBoundaryTestCase:
    """One Python payload and its canonical native record bytes."""

    description: str
    kind: str
    payload: CanonicalValue
    expected_bytes: bytes


@dataclass(frozen=True)
class InvalidSerializationBoundaryTestCase:
    """One Python payload rejected by native canonical conversion."""

    description: str
    payload: object
    expected_error_fragment: str


@dataclass(frozen=True)
class CacheStoreBoundaryTestCase:
    """One typed Python cache record crossing native storage."""

    description: str
    relative_path: str
    kind: str
    payload: CanonicalValue
    expected_available: bool


@dataclass(frozen=True)
class CachePathBoundaryTestCase:
    """One path rejected by the Python storage adapter."""

    description: str
    relative_path: str
    expected_error_fragment: str


@dataclass(frozen=True)
class CacheMutationBoundaryTestCase:
    """One Python callback mutation crossing the native transaction boundary."""

    description: str
    seeded_path: str
    written_path: str
    expected_published: bool
    expected_written: bool
