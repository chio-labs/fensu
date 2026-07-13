"""Conditional and comprehension control-flow fact extraction."""

from __future__ import annotations

import ast
from collections.abc import Mapping
from pathlib import Path
from typing import cast

from strata.analysis._helpers.locations import line_offsets, source_location, source_range
from strata.analysis.models import FunctionConditionalFact, SourceLocation

_comprehension_types: tuple[type[ast.AST], ...] = (
    ast.ListComp,
    ast.SetComp,
    ast.DictComp,
    ast.GeneratorExp,
)
_test_conditional_types: tuple[type[ast.AST], ...] = (
    ast.If,
    ast.Match,
    ast.IfExp,
)


def test_conditional_locations(
    *, path: Path, definitions: tuple[ast.AST, ...]
) -> tuple[SourceLocation, ...]:
    """Return test-policy conditionals inside definition bodies in source order."""

    locations_by_position: dict[tuple[int, int], SourceLocation] = {}
    for definition in definitions:
        body: list[ast.stmt] | None = getattr(definition, "body", None)
        if body is None:
            continue
        for statement in body:
            for node in ast.walk(statement):
                conditional: bool = isinstance(node, _test_conditional_types)
                filtered_comprehension: bool = False
                if isinstance(node, _comprehension_types):
                    comprehension: ast.ListComp | ast.SetComp | ast.DictComp | ast.GeneratorExp = (
                        cast(
                            ast.ListComp | ast.SetComp | ast.DictComp | ast.GeneratorExp,
                            node,
                        )
                    )
                    filtered_comprehension = any(
                        generator.ifs for generator in comprehension.generators
                    ) and not _is_complex_comprehension(comprehension)
                if conditional or filtered_comprehension:
                    location: SourceLocation = source_location(path=path, node=node)
                    locations_by_position[(location.line, location.column)] = location
    return tuple(locations_by_position[position] for position in sorted(locations_by_position))


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


def complex_comprehension_locations(
    *,
    path: Path,
    node_index: Mapping[type[ast.AST], tuple[ast.AST, ...]],
) -> tuple[SourceLocation, ...]:
    """Return complex comprehensions in compatibility index order."""

    nodes: list[ast.AST] = []
    for node_type in _comprehension_types:
        nodes.extend(node_index.get(node_type, ()))
    return tuple(
        source_location(path=path, node=node) for node in nodes if _is_complex_comprehension(node)
    )


def _is_complex_comprehension(node: ast.AST) -> bool:
    return _generator_count(node) > 1 or _contains_nested_comprehension(node)


def _generator_count(node: ast.AST) -> int:
    generators: list[ast.comprehension] | None = getattr(node, "generators", None)
    return len(generators) if generators is not None else 0


def _contains_nested_comprehension(node: ast.AST) -> bool:
    for child in ast.iter_child_nodes(node):
        if any(isinstance(descendant, _comprehension_types) for descendant in ast.walk(child)):
            return True
    return False
