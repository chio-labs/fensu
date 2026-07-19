"""Test case types for persistent cache storage integration."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PersistentStoreTestCase:
    """A disk-backed cache record and expected process-independent result."""

    description: str
    relative_path: str
    kind: str
    writer_count: int
    expected_payload_values: tuple[int, ...]
    expected_temporary_count: int
    expected_miss_count: int = 0
