"""Synchronize and query the configured Fensu Memory index internally."""

from __future__ import annotations

from fensu.memory._helpers.native_operations import query, synchronize
from fensu.memory._helpers.project import resolve_memory_project
from fensu.memory.models import (
    MemoryProject,
    MemoryQueryExecution,
    MemoryQueryResult,
    MemorySyncSummary,
)


def query_memory(*, sql: str, limit: int) -> MemoryQueryExecution:
    """Synchronize memory and run one bounded read-only SQL query."""

    project: MemoryProject = resolve_memory_project()
    sync: MemorySyncSummary = synchronize(project)
    result: MemoryQueryResult = query(project=project, sql=sql, limit=limit)
    return MemoryQueryExecution(project=project, sync=sync, query=result)
