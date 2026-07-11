"""Owned meaningful-return fact extraction."""

from __future__ import annotations

import ast
from collections.abc import Mapping
from fnmatch import fnmatchcase
from pathlib import Path

from strata.analysis.core.helpers.locations import source_location
from strata.analysis.core.models import (
    DiscardedProjectCallFact,
    MeaningfulReturnFact,
    ProjectCallFacts,
    ProjectFunctionFact,
)

_no_return_annotation_names: frozenset[str] = frozenset({"Never", "NoReturn", "None"})
_module_separator: str = "."


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


def project_call_facts(*, path: Path, module: ast.Module) -> ProjectCallFacts:
    """Return resolvable discarded project calls."""

    functions: tuple[ast.FunctionDef | ast.AsyncFunctionDef, ...] = tuple(
        node for node in module.body if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    )
    discarded_calls: list[DiscardedProjectCallFact] = []
    for function in functions:
        shadowed_names: frozenset[str] = _parameter_names(function) | _assigned_locals(function)
        for statement, call in _bare_calls(function):
            target: tuple[str | None, str] | None = _call_target(
                call=call,
                module=module,
                shadowed_names=shadowed_names,
            )
            if target is not None:
                discarded_calls.append(
                    DiscardedProjectCallFact(
                        location=source_location(path=path, node=statement),
                        module_name=target[0],
                        function_name=target[1],
                    )
                )
    return ProjectCallFacts(discarded_calls=tuple(discarded_calls))


def project_function_facts(*, module: ast.Module) -> tuple[ProjectFunctionFact, ...]:
    """Return top-level function result contracts without traversing bodies."""

    return tuple(
        ProjectFunctionFact(name=node.name, meaningful_result=_has_meaningful_result(node))
        for node in module.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    )


def _call_target(
    *, call: ast.Call, module: ast.Module, shadowed_names: frozenset[str]
) -> tuple[str | None, str] | None:
    if isinstance(call.func, ast.Name):
        name: str = call.func.id
        if name in shadowed_names:
            return None
        if any(
            isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name == name
            for node in module.body
        ):
            return None, name
        for node in module.body:
            if not isinstance(node, ast.ImportFrom) or node.level or node.module is None:
                continue
            for alias in node.names:
                if (alias.asname or alias.name) == name:
                    return node.module, alias.name
        return None
    if isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name):
        local_name: str = call.func.value.id
        for node in module.body:
            if not isinstance(node, ast.Import):
                continue
            for alias in node.names:
                if alias.asname is None and _module_separator in alias.name:
                    continue
                if (alias.asname or alias.name) == local_name:
                    return alias.name, call.func.attr
    return None


def _bare_calls(
    function: ast.FunctionDef | ast.AsyncFunctionDef,
) -> tuple[tuple[ast.Expr, ast.Call], ...]:
    calls: list[tuple[ast.Expr, ast.Call]] = []
    for statement in function.body:
        calls.extend(_bare_calls_in_node(statement))
    return tuple(calls)


def _bare_calls_in_node(node: ast.AST) -> tuple[tuple[ast.Expr, ast.Call], ...]:
    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef | ast.Lambda):
        return ()
    if isinstance(node, ast.Expr):
        call: ast.Call | None = _expression_call(node.value)
        if call is not None:
            return ((node, call),)
    calls: list[tuple[ast.Expr, ast.Call]] = []
    for child in ast.iter_child_nodes(node):
        calls.extend(_bare_calls_in_node(child))
    return tuple(calls)


def _expression_call(node: ast.expr) -> ast.Call | None:
    if isinstance(node, ast.Call):
        return node
    if isinstance(node, ast.Await) and isinstance(node.value, ast.Call):
        return node.value
    return None


def _parameter_names(function: ast.FunctionDef | ast.AsyncFunctionDef) -> frozenset[str]:
    args: ast.arguments = function.args
    names: set[str] = {arg.arg for arg in (*args.posonlyargs, *args.args, *args.kwonlyargs)}
    if args.vararg is not None:
        names.add(args.vararg.arg)
    if args.kwarg is not None:
        names.add(args.kwarg.arg)
    return frozenset(names)


def _assigned_locals(function: ast.FunctionDef | ast.AsyncFunctionDef) -> frozenset[str]:
    return frozenset(
        node.id
        for node in ast.walk(function)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)
    )


def _has_meaningful_result(function: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    annotation: ast.expr | None = function.returns
    if annotation is None or (isinstance(annotation, ast.Constant) and annotation.value is None):
        return False
    if isinstance(annotation, ast.Name):
        return annotation.id not in _no_return_annotation_names
    if isinstance(annotation, ast.Attribute):
        return annotation.attr not in _no_return_annotation_names
    if isinstance(annotation, ast.Constant) and isinstance(annotation.value, str):
        return annotation.value.rsplit(".", maxsplit=1)[-1] not in _no_return_annotation_names
    return True


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
