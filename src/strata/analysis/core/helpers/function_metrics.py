"""Shared structural function-metric extraction."""

from __future__ import annotations

import ast
from collections.abc import Mapping
from pathlib import Path

from strata.analysis.core.helpers.locations import source_location
from strata.analysis.core.models import DataclassFact, FunctionFacts, FunctionMetricFact

_exempt_parameters: frozenset[str] = frozenset({"cls", "self"})
_dataclass_decorator_name: str = "dataclass"
_frozen_keyword_name: str = "frozen"


def function_facts(
    *,
    path: Path,
    module: ast.Module,
    node_index: Mapping[type[ast.AST], tuple[ast.AST, ...]],
) -> FunctionFacts:
    """Return shared metrics for all functions and top-level functions."""

    function_nodes: tuple[ast.AST, ...] = (
        *node_index.get(ast.FunctionDef, ()),
        *node_index.get(ast.AsyncFunctionDef, ()),
    )
    if not function_nodes:
        return FunctionFacts(functions=(), top_level=())
    fact_by_node: dict[ast.AST, FunctionMetricFact] = {}
    functions: list[FunctionMetricFact] = []
    for node in function_nodes:
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        fact: FunctionMetricFact = _function_metric_fact(path=path, node=node)
        fact_by_node[node] = fact
        functions.append(fact)
    top_level: tuple[FunctionMetricFact, ...] = tuple(
        fact_by_node[node]
        for node in module.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    )
    return FunctionFacts(functions=tuple(functions), top_level=top_level)


def _function_metric_fact(
    *,
    path: Path,
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> FunctionMetricFact:
    statement_count: int = -1
    call_names: set[str] = set()
    assigned_names: set[str] = set()
    for descendant in ast.walk(node):
        if isinstance(descendant, ast.stmt):
            statement_count += 1
        if isinstance(descendant, ast.Call):
            call_name: str | None = _call_name(descendant)
            if call_name is not None:
                call_names.add(call_name)
        if isinstance(descendant, ast.Assign):
            for target in descendant.targets:
                if isinstance(target, ast.Name):
                    assigned_names.add(target.id)
        if isinstance(descendant, ast.AnnAssign) and isinstance(descendant.target, ast.Name):
            assigned_names.add(descendant.target.id)
    parameter_names: frozenset[str] = _parameter_names(node)
    positional_parameter_count: int = len(
        [
            argument
            for argument in (*node.args.posonlyargs, *node.args.args)
            if argument.arg not in _exempt_parameters
        ]
    )
    return FunctionMetricFact(
        location=source_location(path=path, node=node),
        name=node.name,
        statement_count=statement_count,
        distinct_call_count=len(call_names),
        assigned_local_count=len(assigned_names),
        parameter_count=len(parameter_names),
        positional_parameter_count=positional_parameter_count,
        dunder=node.name.startswith("__") and node.name.endswith("__"),
    )


def _parameter_names(node: ast.FunctionDef | ast.AsyncFunctionDef) -> frozenset[str]:
    arguments: ast.arguments = node.args
    names: set[str] = {
        argument.arg
        for argument in (*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs)
        if argument.arg not in _exempt_parameters
    }
    if arguments.vararg is not None and arguments.vararg.arg not in _exempt_parameters:
        names.add(arguments.vararg.arg)
    if arguments.kwarg is not None and arguments.kwarg.arg not in _exempt_parameters:
        names.add(arguments.kwarg.arg)
    return frozenset(names)


def _call_name(node: ast.Call) -> str | None:
    return _name_from_expr(node.func)


def _name_from_expr(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base: str | None = _name_from_expr(node.value)
        return node.attr if base is None else f"{base}.{node.attr}"
    return None


def dataclass_facts(*, path: Path, module: ast.Module) -> tuple[DataclassFact, ...]:
    """Return top-level dataclass declarations and field metadata."""

    facts: list[DataclassFact] = []
    for node in module.body:
        if not isinstance(node, ast.ClassDef):
            continue
        decorator: ast.expr | None = next(
            (
                candidate
                for candidate in node.decorator_list
                if _decorator_name(candidate).endswith(_dataclass_decorator_name)
            ),
            None,
        )
        if decorator is None:
            continue
        decorator_name: str = _decorator_name(
            decorator.func if isinstance(decorator, ast.Call) else decorator
        )
        facts.append(
            DataclassFact(
                name=node.name,
                location=source_location(path=path, node=node),
                field_names=frozenset(
                    statement.target.id
                    for statement in node.body
                    if isinstance(statement, ast.AnnAssign)
                    and isinstance(statement.target, ast.Name)
                ),
                frozen=_dataclass_call_is_frozen(decorator),
                shape_candidate=decorator_name == _dataclass_decorator_name,
            )
        )
    return tuple(facts)


def _decorator_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent: str = _decorator_name(node.value)
        return node.attr if not parent else f"{parent}.{node.attr}"
    if isinstance(node, ast.Call):
        return _decorator_name(node.func)
    return ""


def _dataclass_call_is_frozen(node: ast.expr) -> bool:
    if not isinstance(node, ast.Call):
        return False
    for keyword in node.keywords:
        if keyword.arg == _frozen_keyword_name and isinstance(keyword.value, ast.Constant):
            return keyword.value.value is True
    return False
