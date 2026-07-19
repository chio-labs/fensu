"""Completely rebuild the configured Fensu Memory index."""

from __future__ import annotations

from fensu.memory._helpers.native_operations import rebuild
from fensu.memory._helpers.project import resolve_memory_project
from fensu.memory.models import MemoryIndexSummary, MemoryProject, MemoryRebuildResult


def rebuild_memory() -> MemoryRebuildResult:
    """Replace the persistent memory index from repository sources."""

    project: MemoryProject = resolve_memory_project()
    summary: MemoryIndexSummary = rebuild(project)
    return MemoryRebuildResult(project=project, summary=summary)
