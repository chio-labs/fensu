"""Function conditional-control-flow fact extraction."""

from __future__ import annotations

import ast
from collections.abc import Mapping
from pathlib import Path

from strata.analysis.core.helpers.locations import line_offsets, source_range
from strata.analysis.core.models import FunctionConditionalFact


def function_conditional_facts(
    *,
    path: Path,
    source: str,
    node_index: Mapping[type[ast.AST], tuple[ast.AST, ...]],
) -> tuple[FunctionConditionalFact, ...]:
    """Return conditional locations grouped in function traversal order."""

    pending: list[tuple[str, tuple[str, ...], ast.AST]] = []
    functions: tuple[ast.AST, ...] = (
        *node_index.get(ast.FunctionDef, ()),
        *node_index.get(ast.AsyncFunctionDef, ()),
    )
    for node in functions:
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        decorator_names: tuple[str, ...] = tuple(
            _decorator_name(decorator) for decorator in node.decorator_list
        )
        for descendant in ast.walk(node):
            if isinstance(descendant, ast.If | ast.IfExp | ast.Match | ast.While):
                pending.append((node.name, decorator_names, descendant))
            elif isinstance(descendant, ast.comprehension):
                for condition in descendant.ifs:
                    pending.append((node.name, decorator_names, condition))
    if not pending:
        return ()
    offsets: tuple[int, ...] = line_offsets(source)
    return tuple(
        FunctionConditionalFact(
            function_name=function_name,
            decorator_names=decorator_names,
            location=source_range(
                path=path,
                source=source,
                line_offsets=offsets,
                node=node,
            ),
        )
        for function_name, decorator_names, node in pending
    )


def _decorator_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent: str = _decorator_name(node.value)
        return node.attr if not parent else f"{parent}.{node.attr}"
    if isinstance(node, ast.Call):
        return _decorator_name(node.func)
    return ""
