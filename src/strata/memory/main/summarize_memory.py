"""Synchronize and summarize the configured Strata Memory index."""

from __future__ import annotations

from strata.memory._helpers.native_operations import overview, synchronize
from strata.memory._helpers.project import resolve_memory_project
from strata.memory.models import (
    MemoryOverview,
    MemoryOverviewResult,
    MemoryProject,
    MemorySyncSummary,
)


def summarize_memory() -> MemoryOverviewResult:
    """Synchronize memory and return its compact operational overview."""

    project: MemoryProject = resolve_memory_project()
    sync: MemorySyncSummary = synchronize(project)
    current: MemoryOverview = overview(project)
    return MemoryOverviewResult(project=project, sync=sync, overview=current)
