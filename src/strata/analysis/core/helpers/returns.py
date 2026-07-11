"""Owned meaningful-return fact extraction."""

from __future__ import annotations

import ast
from collections.abc import Mapping
from fnmatch import fnmatchcase
from pathlib import Path

from strata.analysis.core.helpers.locations import source_location
from strata.analysis.core.models import MeaningfulReturnFact


def meaningful_return_facts(
    *,
    path: Path,
    node_index: Mapping[type[ast.AST], tuple[ast.AST, ...]],
    name_patterns: tuple[str, ...] = (),
) -> tuple[MeaningfulReturnFact, ...]:
    """Return the first meaningful return owned by each function."""

    facts: list[MeaningfulReturnFact] = []
    functions: tuple[ast.AST, ...] = (
        *node_index.get(ast.FunctionDef, ()),
        *node_index.get(ast.AsyncFunctionDef, ()),
    )
    for node in functions:
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        if name_patterns and not any(fnmatchcase(node.name, pattern) for pattern in name_patterns):
            continue
        meaningful_return: ast.Return | None = _owned_meaningful_return(node)
        if meaningful_return is not None:
            facts.append(
                MeaningfulReturnFact(
                    function_name=node.name,
                    location=source_location(path=path, node=meaningful_return),
                )
            )
    return tuple(facts)


def _owned_meaningful_return(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> ast.Return | None:
    for statement in node.body:
        found: ast.Return | None = _meaningful_return(statement)
        if found is not None:
            return found
    return None


def _meaningful_return(node: ast.AST) -> ast.Return | None:
    if isinstance(node, ast.Return):
        if node.value is None:
            return None
        if isinstance(node.value, ast.Constant) and node.value.value is None:
            return None
        return node
    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef | ast.Lambda):
        return None
    for child in ast.iter_child_nodes(node):
        found: ast.Return | None = _meaningful_return(child)
        if found is not None:
            return found
    return None
