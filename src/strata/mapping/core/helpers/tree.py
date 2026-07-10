"""Resolve project-local calls into a recursive call tree."""

from __future__ import annotations

import ast

from strata.mapping.core.models import CallMapNode, FunctionDefinition, UnresolvedCall


def build_tree(
    *,
    root: FunctionDefinition,
    definitions: dict[str, FunctionDefinition],
    depth: int,
) -> CallMapNode:
    """Build a depth-bounded downstream tree with branch-local cycle detection."""

    return _build_node(
        definition=root,
        definitions=definitions,
        remaining_depth=depth,
        ancestors=frozenset(),
    )


def _build_node(
    *,
    definition: FunctionDefinition,
    definitions: dict[str, FunctionDefinition],
    remaining_depth: int,
    ancestors: frozenset[str],
) -> CallMapNode:
    key: str = f"{definition.module_name}.{definition.name}"
    if key in ancestors:
        return CallMapNode(definition=definition, children=(), cycle=True)
    callees, unresolved_calls = _call_targets(definition=definition, definitions=definitions)
    if remaining_depth == 0:
        return CallMapNode(
            definition=definition,
            children=(),
            unresolved_calls=(),
            truncated=bool(callees or unresolved_calls),
        )
    next_ancestors: frozenset[str] = ancestors | {key}
    children: tuple[CallMapNode, ...] = tuple(
        _build_node(
            definition=callee,
            definitions=definitions,
            remaining_depth=remaining_depth - 1,
            ancestors=next_ancestors,
        )
        for callee in callees
    )
    return CallMapNode(
        definition=definition,
        children=children,
        unresolved_calls=unresolved_calls,
    )


def _call_targets(
    *, definition: FunctionDefinition, definitions: dict[str, FunctionDefinition]
) -> tuple[tuple[FunctionDefinition, ...], tuple[UnresolvedCall, ...]]:
    resolved: list[FunctionDefinition] = []
    unresolved: list[UnresolvedCall] = []
    seen: set[str] = set()
    parameter_names: frozenset[str] = _parameter_names(definition.node)
    for call in _owned_calls(definition.node):
        key: str | None = _resolve_call_key(call=call, definition=definition)
        if isinstance(call.func, ast.Name) and call.func.id in parameter_names:
            unresolved.append(
                UnresolvedCall(name=call.func.id, line=call.lineno, reason="parameter call")
            )
            continue
        if key is None or key in seen or key not in definitions:
            continue
        seen.add(key)
        resolved.append(definitions[key])
    return tuple(resolved), tuple(unresolved)


def _owned_calls(node: ast.AST) -> tuple[ast.Call, ...]:
    calls: list[ast.Call] = []
    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef | ast.Lambda):
            continue
        if isinstance(child, ast.Call):
            calls.append(child)
        calls.extend(_owned_calls(child))
    return tuple(calls)


def _resolve_call_key(*, call: ast.Call, definition: FunctionDefinition) -> str | None:
    if isinstance(call.func, ast.Name):
        imported: tuple[str, str] | None = definition.imported_symbols.get(call.func.id)
        if imported is not None:
            return f"{imported[0]}.{imported[1]}"
        return f"{definition.module_name}.{call.func.id}"
    if not isinstance(call.func, ast.Attribute) or not isinstance(call.func.value, ast.Name):
        return None
    imported_module: str | None = definition.imported_modules.get(call.func.value.id)
    if imported_module is None:
        return None
    return f"{imported_module}.{call.func.attr}"


def _parameter_names(node: ast.FunctionDef | ast.AsyncFunctionDef) -> frozenset[str]:
    arguments: ast.arguments = node.args
    names: set[str] = {
        argument.arg
        for argument in (*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs)
    }
    if arguments.vararg is not None:
        names.add(arguments.vararg.arg)
    if arguments.kwarg is not None:
        names.add(arguments.kwarg.arg)
    return frozenset(names)
