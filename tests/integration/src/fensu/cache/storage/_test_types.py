"""Test-case types for persistent native-cache Python boundaries."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PersistentStoreBoundaryTestCase:
    """One cache boundary observed across Python store instances or threads."""

    description: str
    relative_path: str
    kind: str
    values: tuple[int, ...]
    expected_available: bool
