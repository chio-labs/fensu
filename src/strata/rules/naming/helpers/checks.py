"""Rule check functions for the naming family."""

from __future__ import annotations

import ast
from fnmatch import fnmatchcase

from strata.config.core.types import ContractBehavior
from strata.rules.authoring.models import Fault
from strata.rules.authoring.types import RuleContext


def validator_must_not_return(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag meaningful returns from functions under no-return name contracts."""

    patterns: tuple[str, ...] = tuple(
        pattern
        for pattern, behavior in ctx.contracts().items()
        if behavior == ContractBehavior.NO_RETURN
    )
    faults: list[Fault] = []
    for node in (*ctx.nodes(ast.FunctionDef), *ctx.nodes(ast.AsyncFunctionDef)):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        if not any(fnmatchcase(node.name, pattern) for pattern in patterns):
            continue
        meaningful_return: ast.Return | None = returns_meaningful_value(node)
        if meaningful_return is not None:
            faults.append(ctx.fault(meaningful_return))
    return faults


def returns_meaningful_value(
    function_node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> ast.Return | None:
    """Return the first non-None return owned by a function, excluding nested scopes."""

    for statement in function_node.body:
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
