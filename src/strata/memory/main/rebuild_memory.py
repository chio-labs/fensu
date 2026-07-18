"""Completely rebuild the configured Strata Memory index."""

from __future__ import annotations

from strata.memory._helpers.native_operations import rebuild
from strata.memory._helpers.project import resolve_memory_project
from strata.memory.models import MemoryIndexSummary, MemoryProject, MemoryRebuildResult


def rebuild_memory() -> MemoryRebuildResult:
    """Replace the persistent memory index from repository sources."""

    project: MemoryProject = resolve_memory_project()
    summary: MemoryIndexSummary = rebuild(project)
    return MemoryRebuildResult(project=project, summary=summary)
