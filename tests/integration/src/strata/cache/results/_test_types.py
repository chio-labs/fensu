"""Test case types for persistent typed cache records."""

from __future__ import annotations

from dataclasses import dataclass

from strata.cache.results.models import CachedFileResult


@dataclass(frozen=True)
class PersistentTypedResultTestCase:
    """One typed result and expected cross-store persistence behavior."""

    description: str
    relative_path: str
    result: CachedFileResult
    expected_write: bool
    expected_result: CachedFileResult
