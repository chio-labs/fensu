"""Pure-Python conservative call-map provider."""

from __future__ import annotations

from strata.mapping.core.helpers.index import build_function_index, select_function
from strata.mapping.core.helpers.tree import build_tree
from strata.mapping.core.models import CallMapNode, FunctionDefinition, MappingSource


def build_ast_call_map(
    *, sources: tuple[MappingSource, ...], symbol: str, depth: int
) -> CallMapNode:
    """Resolve statically explicit top-level project-function calls."""

    definitions: dict[str, FunctionDefinition] = build_function_index(sources=sources)
    root: FunctionDefinition = select_function(definitions=definitions, symbol=symbol)
    return build_tree(root=root, definitions=definitions, depth=depth)
