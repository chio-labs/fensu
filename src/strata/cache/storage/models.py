"""Versioned persistent cache storage models."""

from __future__ import annotations

from dataclasses import dataclass

from strata.cache.fingerprints.types import CanonicalValue


@dataclass(frozen=True, slots=True)
class CacheRecord:
    """One tagged canonical payload stored under the active cache schema."""

    kind: str
    payload: CanonicalValue
