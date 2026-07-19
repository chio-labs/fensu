"""Synchronize and summarize the configured Fensu Memory index."""

from __future__ import annotations

from fensu.memory._helpers.native_operations import overview, synchronize
from fensu.memory._helpers.project import resolve_memory_project
from fensu.memory.models import (
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
