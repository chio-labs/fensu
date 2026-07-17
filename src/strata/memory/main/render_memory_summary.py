"""Render the compact synchronized Strata Memory summary."""

from __future__ import annotations

from strata.memory.main._render_memory_overview import render_memory_overview
from strata.memory.main.render_memory_sync import render_memory_sync
from strata.memory.models import MemoryOverviewResult, MemorySyncResult


def render_memory_summary(*, result: MemoryOverviewResult, use_color: bool = False) -> str:
    """Return implicit sync status followed by the compact memory overview."""

    sync_result: MemorySyncResult = MemorySyncResult(project=result.project, sync=result.sync)
    return render_memory_sync(
        result=sync_result,
        compact=True,
        use_color=use_color,
    ) + render_memory_overview(result=result, use_color=use_color)
