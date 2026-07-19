"""Synchronize, retrieve, and render a bounded Strata Memory graph."""

from __future__ import annotations

from strata.memory._helpers.graph_rendering import render_graph
from strata.memory._helpers.native_operations import graph, synchronize
from strata.memory._helpers.project import resolve_memory_project
from strata.memory.main.render_memory_sync import render_memory_sync
from strata.memory.models import (
    MemoryGraphExecution,
    MemoryGraphRequest,
    MemoryProject,
    MemorySyncResult,
    MemorySyncSummary,
)
from strata.memory.types import MemoryGraphDirection, MemoryGraphFormat, MemoryGraphRelationship


def run_memory_graph(
    *,
    pattern: str,
    direction: str,
    relationships: tuple[str, ...],
    depth: int,
    max_nodes: int,
    max_edges: int,
    include_archived: bool,
    output_format: str,
    use_color: bool,
) -> tuple[str, str]:
    """Return separated sync and graph output for one graph invocation."""

    selected_format: MemoryGraphFormat = MemoryGraphFormat(output_format)
    request: MemoryGraphRequest = MemoryGraphRequest(
        pattern=pattern,
        direction=MemoryGraphDirection(direction),
        relationships=tuple(MemoryGraphRelationship(value) for value in relationships),
        depth=depth,
        max_nodes=max_nodes,
        max_edges=max_edges,
        include_archived=include_archived,
    )
    project: MemoryProject = resolve_memory_project()
    sync: MemorySyncSummary = synchronize(project)
    execution: MemoryGraphExecution = MemoryGraphExecution(
        project=project,
        sync=sync,
        request=request,
        graph=graph(project=project, request=request),
    )
    graph_color: bool = use_color and selected_format is MemoryGraphFormat.LONG
    sync_text: str = render_memory_sync(
        result=MemorySyncResult(project=execution.project, sync=execution.sync),
        compact=True,
        use_color=graph_color,
    )
    graph_text: str = render_graph(
        result=execution.graph,
        request=execution.request,
        output_format=selected_format,
        use_color=graph_color,
    )
    return sync_text, graph_text
