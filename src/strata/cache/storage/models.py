"""Versioned persistent cache storage models."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from strata.cache.fingerprints.models import CacheFingerprint
from strata.cache.fingerprints.types import CanonicalValue


@dataclass(frozen=True, slots=True)
class CacheRecord:
    """One tagged canonical payload stored under the active cache schema."""

    kind: str
    payload: CanonicalValue
    content_fingerprint: CacheFingerprint | None = field(default=None, compare=False)


@dataclass(frozen=True, slots=True)
class CacheWrite:
    """One logical record update in an atomic cache publication."""

    relative_path: Path
    record: CacheRecord
    encoded: bytes | None = None


@dataclass(frozen=True, slots=True)
class CacheRead:
    """One logical record lookup in a cache read batch."""

    relative_path: Path
    expected_kind: str


@dataclass(frozen=True, slots=True)
class CacheMutation:
    """One transactional publication with an optional unreferenced-record sweep."""

    writes: tuple[CacheWrite, ...]
    swept_prefix: Path | None = None
    retained_paths: tuple[Path, ...] = ()


@dataclass(frozen=True, slots=True)
class CacheMutationOutcome:
    """Storage availability and the mutation applied by one transaction."""

    published: bool
    mutation: CacheMutation | None
