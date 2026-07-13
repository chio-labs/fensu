"""Owned meaningful-return fact extraction."""

from __future__ import annotations

import ast
from collections.abc import Mapping
from fnmatch import fnmatchcase
from pathlib import Path

from strata.analysis._helpers.locations import source_location
from strata.analysis.models import (
    DiscardedProjectCallFact,
    FunctionContractFact,
    ProjectCallFacts,
    ProjectFunctionFact,
)
from strata.analysis.types import ReturnAnnotationCategory

_no_return_annotation_names: frozenset[str] = frozenset({"Never", "NoReturn", "None"})
_module_separator: str = "."


def function_contract_facts(
    *,
    path: Path,
    node_index: Mapping[type[ast.AST], tuple[ast.AST, ...]],
    name_patterns: tuple[str, ...] = (),
) -> tuple[FunctionContractFact, ...]:
    """Return descriptive contracts from one owned-body walk per function."""

    facts: list[FunctionContractFact] = []
    indexed_functions: tuple[ast.AST, ...] = (
        *node_index.get(ast.FunctionDef, ()),
        *node_index.get(ast.AsyncFunctionDef, ()),
    )
    functions: tuple[ast.FunctionDef | ast.AsyncFunctionDef, ...] = tuple(
        sorted(
            (
                node
                for node in indexed_functions
                if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
            ),
            key=lambda node: (node.lineno, node.col_offset),
        )
    )
    for node in functions:
        if name_patterns and not any(fnmatchcase(node.name, pattern) for pattern in name_patterns):
            continue
        meaningful_return, contains_yield = _owned_return_shape(node)
        annotation_category, annotation = _return_annotation(node.returns)
        facts.append(
            FunctionContractFact(
                function_name=node.name,
                location=source_location(path=path, node=node),
                return_annotation_category=annotation_category,
                return_annotation=annotation,
                contains_yield=contains_yield,
                meaningful_return_location=(
                    source_location(path=path, node=meaningful_return)
                    if meaningful_return is not None
                    else None
                ),
            )
        )
    return tuple(facts)


def _return_annotation(
    annotation: ast.expr | None,
) -> tuple[ReturnAnnotationCategory, str]:
    if annotation is None:
        return ReturnAnnotationCategory.MISSING, "missing"
    normalized: ast.expr = annotation
    display: str = ast.unparse(annotation)
    if isinstance(annotation, ast.Constant) and isinstance(annotation.value, str):
        display = annotation.value
        try:
            normalized = ast.parse(annotation.value, mode="eval").body
        except SyntaxError:
            return ReturnAnnotationCategory.OTHER, display
    if isinstance(normalized, ast.Constant) and normalized.value is None:
        return ReturnAnnotationCategory.NONE, display
    terminal_name: str | None = _annotation_terminal_name(normalized)
    categories: dict[str, ReturnAnnotationCategory] = {
        "None": ReturnAnnotationCategory.NONE,
        "NoReturn": ReturnAnnotationCategory.NONE,
        "Never": ReturnAnnotationCategory.NONE,
        "bool": ReturnAnnotationCategory.BOOL,
        "TypeGuard": ReturnAnnotationCategory.TYPE_GUARD,
        "TypeIs": ReturnAnnotationCategory.TYPE_IS,
        "Iterator": ReturnAnnotationCategory.ITERATOR,
        "Generator": ReturnAnnotationCategory.GENERATOR,
        "AsyncIterator": ReturnAnnotationCategory.ASYNC_ITERATOR,
        "AsyncGenerator": ReturnAnnotationCategory.ASYNC_GENERATOR,
    }
    return categories.get(terminal_name, ReturnAnnotationCategory.OTHER), display


def _annotation_terminal_name(annotation: ast.expr) -> str | None:
    value: ast.expr = annotation.value if isinstance(annotation, ast.Subscript) else annotation
    if isinstance(value, ast.Name):
        return value.id
    if isinstance(value, ast.Attribute):
        return value.attr
    return None


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


def _owned_return_shape(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> tuple[ast.Return | None, bool]:
    meaningful_return: ast.Return | None = None
    contains_yield: bool = False
    for statement in node.body:
        found, statement_yields = _return_shape(statement)
        if meaningful_return is None and found is not None:
            meaningful_return = found
        contains_yield = contains_yield or statement_yields
    return meaningful_return, contains_yield


def _return_shape(node: ast.AST) -> tuple[ast.Return | None, bool]:
    if isinstance(node, ast.Return):
        if node.value is None:
            return None, False
        if isinstance(node.value, ast.Constant) and node.value.value is None:
            return None, False
        return node, False
    if isinstance(node, ast.Yield | ast.YieldFrom):
        return None, True
    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef | ast.Lambda):
        return None, False
    meaningful_return: ast.Return | None = None
    contains_yield: bool = False
    for child in ast.iter_child_nodes(node):
        found, child_yields = _return_shape(child)
        if meaningful_return is None and found is not None:
            meaningful_return = found
        contains_yield = contains_yield or child_yields
    return meaningful_return, contains_yield
