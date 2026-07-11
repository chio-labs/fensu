"""Versioned persistent cache storage models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from strata.cache.fingerprints.types import CanonicalValue


@dataclass(frozen=True, slots=True)
class CacheRecord:
    """One tagged canonical payload stored under the active cache schema."""

    kind: str
    payload: CanonicalValue


@dataclass(frozen=True, slots=True)
class CacheWrite:
    """One logical record update in an atomic cache publication."""

    relative_path: Path
    record: CacheRecord


@dataclass(frozen=True, slots=True)
class CacheRead:
    """One logical record lookup in a cache read batch."""

    relative_path: Path
    expected_kind: str
