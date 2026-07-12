"""Pure-Python conservative call-map provider."""

from __future__ import annotations

from strata.mapping.core.helpers.index import build_project_index, select_function
from strata.mapping.core.helpers.tree import build_tree
from strata.mapping.core.models import CallMapNode, FunctionDefinition, MappingSource, ProjectIndex


def build_ast_call_map(
    *, sources: tuple[MappingSource, ...], symbol: str, depth: int
) -> CallMapNode:
    """Resolve statically explicit project function and method calls."""

    index: ProjectIndex = build_project_index(sources=sources)
    root: FunctionDefinition = select_function(definitions=index.functions, symbol=symbol)
    return build_tree(root=root, index=index, depth=depth)
