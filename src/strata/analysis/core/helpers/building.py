"""Build the Python reference analysis and compatibility indexes."""

from __future__ import annotations

import ast
from collections import defaultdict, deque
from collections.abc import Mapping
from pathlib import Path

from strata.analysis.core.classes.file_analysis import PythonFileAnalysis
from strata.analysis.core.types import AnalysisBuild


def build_python_analysis(*, path: Path, source: str, module: ast.Module) -> AnalysisBuild:
    """Build analysis and compatibility indexes in one breadth-first traversal."""

    nodes, node_index, parent_by_node, children_by_node = _index_nodes(module)
    analysis: PythonFileAnalysis = PythonFileAnalysis(
        path=path,
        source=source,
        nodes=nodes,
        node_index=node_index,
        parent_by_node=parent_by_node,
        children_by_node=children_by_node,
    )
    frozen_index: Mapping[type[ast.AST], tuple[ast.AST, ...]] = {
        node_type: tuple(indexed_nodes) for node_type, indexed_nodes in node_index.items()
    }
    return AnalysisBuild(
        analysis=analysis,
        node_index=frozen_index,
        parent_by_node=parent_by_node,
    )


def _index_nodes(
    module: ast.Module,
) -> tuple[
    tuple[ast.AST, ...],
    Mapping[type[ast.AST], tuple[ast.AST, ...]],
    Mapping[ast.AST, ast.AST],
    Mapping[ast.AST, tuple[ast.AST, ...]],
]:
    node_index: defaultdict[type[ast.AST], list[ast.AST]] = defaultdict(list)
    parent_by_node: dict[ast.AST, ast.AST] = {}
    children_by_node: dict[ast.AST, tuple[ast.AST, ...]] = {}
    nodes: list[ast.AST] = []
    pending: deque[ast.AST] = deque((module,))
    while pending:
        node: ast.AST = pending.popleft()
        nodes.append(node)
        node_index[type(node)].append(node)
        children: tuple[ast.AST, ...] = tuple(ast.iter_child_nodes(node))
        children_by_node[node] = children
        for child in children:
            parent_by_node[child] = node
            pending.append(child)
    return (
        tuple(nodes),
        {node_type: tuple(indexed_nodes) for node_type, indexed_nodes in node_index.items()},
        parent_by_node,
        children_by_node,
    )
