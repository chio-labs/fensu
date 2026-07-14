"""Build CPython breadth-first syntax indexes for parity comparison."""

from __future__ import annotations

import ast
from collections import defaultdict, deque
from collections.abc import Mapping


def index_module_nodes(
    module: ast.Module,
) -> tuple[
    tuple[ast.AST, ...],
    Mapping[type[ast.AST], tuple[ast.AST, ...]],
    Mapping[ast.AST, ast.AST],
]:
    """Return breadth-first nodes, per-type indexes, and parent links."""

    node_index: defaultdict[type[ast.AST], list[ast.AST]] = defaultdict(list)
    parent_by_node: dict[ast.AST, ast.AST] = {}
    nodes: list[ast.AST] = []
    pending: deque[ast.AST] = deque((module,))
    while pending:
        node: ast.AST = pending.popleft()
        nodes.append(node)
        node_index[type(node)].append(node)
        for child in ast.iter_child_nodes(node):
            parent_by_node[child] = node
            pending.append(child)
    frozen_index: dict[type[ast.AST], tuple[ast.AST, ...]] = {
        node_type: tuple(indexed_nodes) for node_type, indexed_nodes in node_index.items()
    }
    return tuple(nodes), frozen_index, parent_by_node
