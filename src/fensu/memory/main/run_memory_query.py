"""Synchronize, query, and render Fensu Memory SQL."""

from __future__ import annotations

from fensu.memory.main._query_memory import query_memory
from fensu.memory.main._render_memory_query import render_memory_query
from fensu.memory.main.render_memory_sync import render_memory_sync
from fensu.memory.models import MemoryQueryExecution, MemorySyncResult
from fensu.memory.types import MemoryQueryFormat


def run_memory_query(
    *,
    sql: str,
    limit: int,
    output_format: str,
    use_color: bool,
) -> tuple[str, str]:
    """Return machine-safe sync and query output for one SQL invocation."""

    selected_format: MemoryQueryFormat = MemoryQueryFormat(output_format)
    execution: MemoryQueryExecution = query_memory(sql=sql, limit=limit)
    query_color: bool = use_color and selected_format in {
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
        output_format=selected_format,
        use_color=query_color,
    )
    return sync_text, query_text
