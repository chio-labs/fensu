"""AST helper surface owned by evaluation."""

from __future__ import annotations

import ast
from collections import defaultdict, deque
from collections.abc import Mapping

_comprehension_types: tuple[type[ast.AST], ...] = (
    ast.ListComp,
    ast.SetComp,
    ast.DictComp,
    ast.GeneratorExp,
)


def build_ast_indexes(
    module: ast.Module,
) -> tuple[Mapping[type[ast.AST], tuple[ast.AST, ...]], Mapping[ast.AST, ast.AST]]:
    """Build node-type and parent indexes in one breadth-first traversal."""

    index: defaultdict[type[ast.AST], list[ast.AST]] = defaultdict(list)
    parents: dict[ast.AST, ast.AST] = {}
    pending: deque[ast.AST] = deque((module,))
    while pending:
        node: ast.AST = pending.popleft()
        index[type(node)].append(node)
        for child in ast.iter_child_nodes(node):
            parents[child] = node
            pending.append(child)
    return {node_type: tuple(nodes) for node_type, nodes in index.items()}, parents


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


def complex_comprehensions(
    node_index: Mapping[type[ast.AST], tuple[ast.AST, ...]],
) -> tuple[ast.AST, ...]:
    """Return comprehensions with multiple generators or a nested comprehension."""

    comprehension_nodes: list[ast.AST] = []
    for node_type in _comprehension_types:
        comprehension_nodes.extend(node_index.get(node_type, ()))
    return tuple(
        node
        for node in comprehension_nodes
        if _generator_count(node) > 1 or _contains_nested_comprehension(node)
    )


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


def _generator_count(node: ast.AST) -> int:
    generators: list[ast.comprehension] | None = getattr(node, "generators", None)
    return len(generators) if generators is not None else 0


def _contains_nested_comprehension(node: ast.AST) -> bool:
    for child in ast.iter_child_nodes(node):
        if any(isinstance(descendant, _comprehension_types) for descendant in ast.walk(child)):
            return True
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
