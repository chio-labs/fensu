"""Deterministic human and machine rendering for memory graphs."""

from __future__ import annotations

import json
from dataclasses import asdict

from fensu.memory._helpers.human_rendering import heading
from fensu.memory.constants import ARCHIVE_STATE_ARCHIVED, RESOLUTION_STATUS_RESOLVED
from fensu.memory.models import (
    MemoryGraphEdge,
    MemoryGraphNode,
    MemoryGraphRequest,
    MemoryGraphResult,
)
from fensu.memory.types import MemoryGraphFormat


def render_graph(
    *,
    result: MemoryGraphResult,
    request: MemoryGraphRequest,
    output_format: MemoryGraphFormat,
    use_color: bool,
) -> str:
    """Render one bounded graph in the requested format."""

    if output_format is MemoryGraphFormat.JSON:
        return _json_graph(result=result, request=request)
    return _long_graph(result=result, request=request, use_color=use_color)


def _json_graph(*, result: MemoryGraphResult, request: MemoryGraphRequest) -> str:
    payload: dict[str, object] = {
        "depth": request.depth,
        "direction": request.direction.value,
        "edges": [asdict(edge) for edge in result.edges],
        "include_archived": request.include_archived,
        "limits": {"max_edges": request.max_edges, "max_nodes": request.max_nodes},
        "nodes": [asdict(node) for node in result.nodes],
        "pattern": request.pattern,
        "relationships": [value.value for value in request.relationships],
        "roots": list(result.roots),
        "selection": result.selection,
        "truncated": {
            "edges": result.edge_budget_exhausted,
            "nodes": result.node_budget_exhausted,
        },
    }
    return json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n"


def _long_graph(*, result: MemoryGraphResult, request: MemoryGraphRequest, use_color: bool) -> str:
    node_lookup: dict[str, MemoryGraphNode] = {node.identity: node for node in result.nodes}
    lines: list[str] = [heading(value="Memory graph", use_color=use_color)]
    lines.append(
        f"Selection: {result.selection} ({len(result.roots)} root(s)), "
        f"{request.direction.value}, depth {request.depth}"
    )
    lines.extend(("", f"Nodes ({len(result.nodes)}):"))
    for node in result.nodes:
        marker: str = "root" if node.root else f"depth {node.depth}"
        archived: str = ", archived" if node.archive_state == ARCHIVE_STATE_ARCHIVED else ""
        title: str = node.title or node.basename
        lines.append(
            f"  [{marker}{archived}] {title} ({node.artifact_kind}) "
            f"<{node.identity}> {node.repository_relative_path}"
        )
    lines.extend(("", f"Edges ({len(result.edges)}):"))
    for edge in result.edges:
        lines.append(_edge_line(edge=edge, nodes=node_lookup))
    lines.extend(("", _budget_line(result=result, request=request)))
    return "\n".join(lines) + "\n"


def _edge_line(*, edge: MemoryGraphEdge, nodes: dict[str, MemoryGraphNode]) -> str:
    source: str = _node_label(identity=edge.source_document_identity, nodes=nodes)
    target: str = (
        _node_label(identity=edge.target_document_identity, nodes=nodes)
        if edge.resolution_status == RESOLUTION_STATUS_RESOLVED
        and edge.target_document_identity is not None
        else edge.authored_target
    )
    labels: list[str] = [edge.resolution_status]
    target_node: MemoryGraphNode | None = (
        nodes.get(edge.target_document_identity) if edge.target_document_identity else None
    )
    if target_node is not None and target_node.archive_state == ARCHIVE_STATE_ARCHIVED:
        labels.append(ARCHIVE_STATE_ARCHIVED)
    if edge.cycle:
        labels.append("cycle")
    return f"  {source} --{edge.relationship}--> {target} [{', '.join(labels)}]"


def _node_label(*, identity: str, nodes: dict[str, MemoryGraphNode]) -> str:
    node: MemoryGraphNode | None = nodes.get(identity)
    return identity if node is None else f"{node.title or node.basename} <{identity}>"


def _budget_line(*, result: MemoryGraphResult, request: MemoryGraphRequest) -> str:
    node_state: str = "exhausted" if result.node_budget_exhausted else "available"
    edge_state: str = "exhausted" if result.edge_budget_exhausted else "available"
    return (
        f"Budgets: nodes {len(result.nodes)}/{request.max_nodes} ({node_state}); "
        f"edges {len(result.edges)}/{request.max_edges} ({edge_state})"
    )
