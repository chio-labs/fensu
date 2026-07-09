"""AST helper surface owned by evaluation."""

from __future__ import annotations

import ast
from collections import defaultdict
from collections.abc import Mapping


def build_node_index(module: ast.Module) -> Mapping[type[ast.AST], tuple[ast.AST, ...]]:
    """Build a shared node index with one AST walk."""

    index: defaultdict[type[ast.AST], list[ast.AST]] = defaultdict(list)
    for node in ast.walk(module):
        index[type(node)].append(node)
    return {node_type: tuple(nodes) for node_type, nodes in index.items()}


def build_parent_map(module: ast.Module) -> Mapping[ast.AST, ast.AST]:
    """Build child -> parent links for context-sensitive helpers."""

    parents: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(module):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent
    return parents


def call_name(node: ast.Call) -> str | None:
    """Return the dotted name called by a Call node when statically knowable."""

    return _name_from_expr(node.func)


def base_name(node: ast.expr) -> str | None:
    """Return the leftmost base name of an expression when statically knowable."""

    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return base_name(node.value)
    if isinstance(node, ast.Call):
        return base_name(node.func)
    return None


def top_level_functions(module: ast.Module) -> tuple[ast.AST, ...]:
    """Return top-level function and async-function definitions."""

    return tuple(
        node for node in module.body if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    )


def non_docstring_body(module: ast.Module) -> list[ast.stmt]:
    """Return module body without a leading docstring expression."""

    if len(module.body) == 0:
        return []
    first: ast.stmt = module.body[0]
    if (
        isinstance(first, ast.Expr)
        and isinstance(first.value, ast.Constant)
        and isinstance(first.value.value, str)
    ):
        return list(module.body[1:])
    return list(module.body)


def distinct_callees(fn: ast.AST) -> frozenset[str]:
    """Return distinct statically-known call names within a function node."""

    names: set[str] = set()
    for node in ast.walk(fn):
        if isinstance(node, ast.Call):
            name: str | None = call_name(node)
            if name is not None:
                names.add(name)
    return frozenset(names)


def assigned_locals(fn: ast.AST) -> frozenset[str]:
    """Return names assigned within a function node."""

    names: set[str] = set()
    for node in ast.walk(fn):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            names.add(node.id)
    return frozenset(names)


def parameter_names(fn: ast.AST) -> frozenset[str]:
    """Return parameter names for a function or async function node."""

    if not isinstance(fn, ast.FunctionDef | ast.AsyncFunctionDef):
        return frozenset()
    args: ast.arguments = fn.args
    names: set[str] = {arg.arg for arg in (*args.posonlyargs, *args.args, *args.kwonlyargs)}
    if args.vararg is not None:
        names.add(args.vararg.arg)
    if args.kwarg is not None:
        names.add(args.kwarg.arg)
    return frozenset(names)


def inside_loop(*, node: ast.AST, parent_by_node: Mapping[ast.AST, ast.AST]) -> bool:
    """Return whether a node is nested inside a for/while loop."""

    current: ast.AST | None = node
    while current is not None:
        if isinstance(current, ast.For | ast.AsyncFor | ast.While):
            return True
        current = parent_by_node.get(current)
    return False


def _name_from_expr(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base: str | None = _name_from_expr(node.value)
        if base is None:
            return node.attr
        return f"{base}.{node.attr}"
    return None
