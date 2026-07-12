"""Build a call tree through symbol point lookups."""

from strata.mapping.helpers.tree import build_tree
from strata.mapping.models import CallMapNode, FunctionDefinition
from strata.mapping.types import SymbolResolver


def build_mapping_tree(
    *, root: FunctionDefinition, resolver: SymbolResolver, depth: int
) -> CallMapNode:
    """Build one depth-bounded downstream call tree."""

    return build_tree(root=root, index=resolver, depth=depth)
