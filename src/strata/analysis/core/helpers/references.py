"""Import and attribute-reference fact extraction."""

from __future__ import annotations

import ast
from collections.abc import Mapping
from pathlib import Path

from strata.analysis.core.helpers.locations import source_location
from strata.analysis.core.models import (
    AttributeReferenceFact,
    ImportAliasFact,
    ImportFact,
    ReferenceFacts,
)


def reference_facts(
    *,
    path: Path,
    nodes: tuple[ast.AST, ...],
    node_index: Mapping[type[ast.AST], tuple[ast.AST, ...]],
) -> ReferenceFacts:
    """Return grouped imports and breadth-first reference events."""

    reference_nodes: tuple[ast.AST, ...] = (
        *node_index.get(ast.ImportFrom, ()),
        *node_index.get(ast.Import, ()),
        *node_index.get(ast.Attribute, ()),
    )
    if not reference_nodes:
        return ReferenceFacts(imports=(), events=())
    import_by_node: dict[ast.AST, ImportFact] = {}
    imports: list[ImportFact] = []
    for node in (*node_index.get(ast.ImportFrom, ()), *node_index.get(ast.Import, ())):
        if not isinstance(node, ast.ImportFrom | ast.Import):
            continue
        fact: ImportFact = _import_fact(path=path, node=node)
        import_by_node[node] = fact
        imports.append(fact)
    events: list[ImportFact | AttributeReferenceFact] = []
    for node in nodes:
        import_fact: ImportFact | None = import_by_node.get(node)
        if import_fact is not None:
            events.append(import_fact)
        elif isinstance(node, ast.Attribute):
            events.append(
                AttributeReferenceFact(
                    location=source_location(path=path, node=node),
                    base_name=_attribute_base_name(node.value),
                    attribute_name=node.attr,
                )
            )
    return ReferenceFacts(imports=tuple(imports), events=tuple(events))


def _import_fact(
    *,
    path: Path,
    node: ast.Import | ast.ImportFrom,
) -> ImportFact:
    if isinstance(node, ast.ImportFrom):
        module_parts: tuple[str, ...] = tuple(node.module.split(".")) if node.module else ()
        aliases: tuple[ImportAliasFact, ...] = tuple(
            ImportAliasFact(
                imported_name=alias.name,
                imported_parts=tuple(alias.name.split(".")),
                bound_name=alias.asname or alias.name,
            )
            for alias in node.names
        )
        relative_level: int = node.level
        from_import: bool = True
    else:
        module_parts = ()
        aliases = tuple(
            ImportAliasFact(
                imported_name=alias.name,
                imported_parts=tuple(alias.name.split(".")),
                bound_name=alias.asname or alias.name.split(".")[-1],
            )
            for alias in node.names
        )
        relative_level = 0
        from_import = False
    return ImportFact(
        location=source_location(path=path, node=node),
        module_parts=module_parts,
        aliases=aliases,
        relative_level=relative_level,
        from_import=from_import,
    )


def _attribute_base_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return _attribute_base_name(node.value)
    return None
