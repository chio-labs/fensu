"""Synchronize the persistent Fensu Memory index."""

from __future__ import annotations

from fensu.memory._helpers.native_operations import synchronize
from fensu.memory._helpers.project import resolve_memory_project
from fensu.memory.models import MemoryProject, MemorySyncResult, MemorySyncSummary


def sync_memory() -> MemorySyncResult:
    """Synchronize configured repository sources into the memory index."""

    project: MemoryProject = resolve_memory_project()
    summary: MemorySyncSummary = synchronize(project)
    return MemorySyncResult(project=project, sync=summary)
