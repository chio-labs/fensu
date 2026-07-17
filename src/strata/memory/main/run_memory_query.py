"""Synchronize, query, and render Strata Memory SQL."""

from __future__ import annotations

from strata.memory.main._query_memory import query_memory
from strata.memory.main._render_memory_query import render_memory_query
from strata.memory.main.render_memory_sync import render_memory_sync
from strata.memory.models import MemoryQueryExecution, MemorySyncResult
from strata.memory.types import MemoryQueryFormat


def run_memory_query(
    *,
    sql: str,
    limit: int,
    output_format: MemoryQueryFormat,
    use_color: bool,
) -> tuple[str, str]:
    """Return machine-safe sync and query output for one SQL invocation."""

    execution: MemoryQueryExecution = query_memory(sql=sql, limit=limit)
    query_color: bool = use_color and output_format in {
        MemoryQueryFormat.LONG,
        MemoryQueryFormat.TABLE,
    }
    query_sync: MemorySyncResult = MemorySyncResult(
        project=execution.project,
        sync=execution.sync,
    )
    sync_text: str = render_memory_sync(result=query_sync, compact=True, use_color=query_color)
    query_text: str = render_memory_query(
        result=execution.query,
        output_format=output_format,
        use_color=query_color,
    )
    return sync_text, query_text
