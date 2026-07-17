"""Render one Strata Memory query result."""

from __future__ import annotations

from strata.memory._helpers.human_rendering import query_long, query_table
from strata.memory._helpers.structured_rendering import query_csv, query_json
from strata.memory.exceptions import MemoryOperationError
from strata.memory.models import MemoryQueryResult
from strata.memory.types import MemoryQueryFormat


def render_memory_query(
    *,
    result: MemoryQueryResult,
    output_format: MemoryQueryFormat,
    use_color: bool = False,
) -> str:
    """Render a query result in the selected deterministic format."""

    if output_format is MemoryQueryFormat.LONG:
        return query_long(result=result, use_color=use_color)
    if output_format is MemoryQueryFormat.TABLE:
        return query_table(result=result, use_color=use_color)
    if output_format is MemoryQueryFormat.JSON:
        return query_json(result)
    if output_format is MemoryQueryFormat.CSV:
        return query_csv(result)
    raise MemoryOperationError(f"Unsupported memory query format: {output_format}")
