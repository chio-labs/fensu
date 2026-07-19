"""Index CPython syntax into shared traversal-order compatibility structures."""

from __future__ import annotations

import ast
from collections import defaultdict, deque

from strata.analysis.types import SyntaxIndexes


def index_module_nodes(*, module: ast.Module) -> SyntaxIndexes:
    """Index one parsed module in a single breadth-first traversal."""

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
    return SyntaxIndexes(
        nodes=tuple(nodes),
        node_index={
            node_type: tuple(indexed_nodes) for node_type, indexed_nodes in node_index.items()
        },
        parent_by_node=parent_by_node,
    )
