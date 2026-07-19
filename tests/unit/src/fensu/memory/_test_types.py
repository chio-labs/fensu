"""Test case types for Fensu Memory rendering."""

from __future__ import annotations

from dataclasses import dataclass

from fensu.memory.models import (
    MemoryCheckResult,
    MemoryGraphRequest,
    MemoryGraphResult,
    MemoryOverviewResult,
    MemoryQueryResult,
    MemoryRebuildResult,
    MemorySchemaResult,
    MemorySyncResult,
)
from fensu.memory.types import MemoryGraphFormat, MemoryQueryFormat


@dataclass(frozen=True)
class MemoryQueryRenderTestCase:
    """One query format and its complete rendered contract."""

    description: str
    result: MemoryQueryResult
    output_format: MemoryQueryFormat
    expected_output: str


@dataclass(frozen=True)
class MemorySchemaRenderTestCase:
    """Structured schema metadata and expected human output."""

    description: str
    result: MemorySchemaResult
    expected_output: str


@dataclass(frozen=True)
class MemoryOverviewRenderTestCase:
    """Compact plan counts and expected human output."""

    description: str
    result: MemoryOverviewResult
    expected_output: str


@dataclass(frozen=True)
class MemorySyncRenderTestCase:
    """Implicit sync state and expected concise output."""

    description: str
    result: MemorySyncResult
    compact: bool
    expected_output: str


@dataclass(frozen=True)
class MemoryRebuildRenderTestCase:
    """Complete rebuild counts and expected human output."""

    description: str
    result: MemoryRebuildResult
    expected_output: str


@dataclass(frozen=True)
class MemoryCheckRenderTestCase:
    """Direct-source findings and expected standard diagnostic output."""

    description: str
    result: MemoryCheckResult
    expected_output: str
    expected_fault_count: int


@dataclass(frozen=True)
class MemoryGraphRenderTestCase:
    """One bounded graph format and its complete rendered contract."""

    description: str
    result: MemoryGraphResult
    request: MemoryGraphRequest
    output_format: MemoryGraphFormat
    expected_output: str
