"""Lexical-scope analysis for outer-state mutation."""

from __future__ import annotations

import ast

_mutator_methods: frozenset[str] = frozenset(
    {"add", "append", "clear", "extend", "insert", "pop", "remove", "setdefault", "update"}
)
_function_nodes: tuple[type[ast.AST], ...] = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)
_comprehension_nodes: tuple[type[ast.AST], ...] = (
    ast.DictComp,
    ast.GeneratorExp,
    ast.ListComp,
    ast.SetComp,
)


def outer_state_mutations(*, module: ast.Module) -> tuple[ast.AST, ...]:
    """Return mutations resolving to module or enclosing-function bindings."""

    module_bindings: frozenset[str] = _scope_bindings(nodes=module.body, include_imports=False)
    return _nested_scope_mutations(
        nodes=module.body,
        module_bindings=module_bindings,
        enclosing_bindings=frozenset(),
    )


def _nested_scope_mutations(
    *,
    nodes: list[ast.stmt] | tuple[ast.AST, ...],
    module_bindings: frozenset[str],
    enclosing_bindings: frozenset[str],
) -> tuple[ast.AST, ...]:
    faults: list[ast.AST] = []
    for node in nodes:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            local_bindings: frozenset[str] = _function_bindings(node=node)
            global_names, nonlocal_names = _function_declarations(node=node)
            faults.extend(
                _owned_mutations(
                    nodes=tuple(node.body),
                    local_bindings=local_bindings,
                    outer_bindings=module_bindings | enclosing_bindings,
                    global_names=global_names,
                    nonlocal_names=nonlocal_names,
                    shadowed_names=frozenset(),
                )
            )
            faults.extend(
                _nested_scope_mutations(
                    nodes=tuple(node.body),
                    module_bindings=module_bindings,
                    enclosing_bindings=enclosing_bindings | local_bindings,
                )
            )
            continue
        if isinstance(node, ast.Lambda):
            local_bindings = _argument_names(arguments=node.args)
            faults.extend(
                _owned_mutations(
                    nodes=(node.body,),
                    local_bindings=local_bindings,
                    outer_bindings=module_bindings | enclosing_bindings,
                    global_names=frozenset(),
                    nonlocal_names=frozenset(),
                    shadowed_names=frozenset(),
                )
            )
            continue
        if isinstance(node, ast.ClassDef):
            faults.extend(
                _nested_scope_mutations(
                    nodes=tuple(node.body),
                    module_bindings=module_bindings,
                    enclosing_bindings=enclosing_bindings,
                )
            )
            continue
        faults.extend(
            _nested_scope_mutations(
                nodes=tuple(ast.iter_child_nodes(node)),
                module_bindings=module_bindings,
                enclosing_bindings=enclosing_bindings,
            )
        )
    return tuple(faults)


def _owned_mutations(
    *,
    nodes: tuple[ast.AST, ...],
    local_bindings: frozenset[str],
    outer_bindings: frozenset[str],
    global_names: frozenset[str],
    nonlocal_names: frozenset[str],
    shadowed_names: frozenset[str],
) -> tuple[ast.AST, ...]:
    faults: list[ast.AST] = []
    for node in nodes:
        if isinstance(node, (*_function_nodes, ast.ClassDef)):
            continue
        if isinstance(node, ast.DictComp | ast.GeneratorExp | ast.ListComp | ast.SetComp):
            comprehension_bindings: frozenset[str] = frozenset(
                name
                for generator in node.generators
                for name in _target_names(target=generator.target)
            )
            faults.extend(
                _owned_mutations(
                    nodes=tuple(ast.iter_child_nodes(node)),
                    local_bindings=local_bindings,
                    outer_bindings=outer_bindings,
                    global_names=global_names,
                    nonlocal_names=nonlocal_names,
                    shadowed_names=shadowed_names | comprehension_bindings,
                )
            )
            continue
        mutation: ast.AST | None = _outer_mutation(
            node=node,
            local_bindings=local_bindings,
            outer_bindings=outer_bindings,
            global_names=global_names,
            nonlocal_names=nonlocal_names,
            shadowed_names=shadowed_names,
        )
        if mutation is not None:
            faults.append(mutation)
        faults.extend(
            _owned_mutations(
                nodes=tuple(ast.iter_child_nodes(node)),
                local_bindings=local_bindings,
                outer_bindings=outer_bindings,
                global_names=global_names,
                nonlocal_names=nonlocal_names,
                shadowed_names=shadowed_names,
            )
        )
    return tuple(faults)


def _outer_mutation(
    *,
    node: ast.AST,
    local_bindings: frozenset[str],
    outer_bindings: frozenset[str],
    global_names: frozenset[str],
    nonlocal_names: frozenset[str],
    shadowed_names: frozenset[str],
) -> ast.AST | None:
    targets: tuple[ast.expr, ...] = ()
    if isinstance(node, ast.Assign):
        targets = tuple(node.targets)
    elif isinstance(node, ast.AnnAssign | ast.AugAssign | ast.NamedExpr):
        targets = (node.target,)
    elif isinstance(node, ast.Delete):
        targets = tuple(node.targets)
    for target in targets:
        name: str | None = _mutation_root_name(target=target)
        if name is not None and _name_resolves_outer(
            name=name,
            direct_name=isinstance(target, ast.Name),
            local_bindings=local_bindings,
            outer_bindings=outer_bindings,
            global_names=global_names,
            nonlocal_names=nonlocal_names,
            shadowed_names=shadowed_names,
        ):
            return target
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        if node.func.attr not in _mutator_methods:
            return None
        name = _root_name(node=node.func.value)
        if name is not None and _name_resolves_outer(
            name=name,
            direct_name=False,
            local_bindings=local_bindings,
            outer_bindings=outer_bindings,
            global_names=global_names,
            nonlocal_names=nonlocal_names,
            shadowed_names=shadowed_names,
        ):
            return node
    return None


def _name_resolves_outer(
    *,
    name: str,
    direct_name: bool,
    local_bindings: frozenset[str],
    outer_bindings: frozenset[str],
    global_names: frozenset[str],
    nonlocal_names: frozenset[str],
    shadowed_names: frozenset[str],
) -> bool:
    if name in shadowed_names:
        return False
    if name in global_names or name in nonlocal_names:
        return True
    if direct_name or name in local_bindings:
        return False
    return name in outer_bindings


def _function_bindings(*, node: ast.FunctionDef | ast.AsyncFunctionDef) -> frozenset[str]:
    global_names, nonlocal_names = _function_declarations(node=node)
    return (
        (
            _argument_names(arguments=node.args)
            | _scope_bindings(nodes=node.body, include_imports=True)
        )
        - global_names
        - nonlocal_names
    )


def _function_declarations(
    *, node: ast.FunctionDef | ast.AsyncFunctionDef
) -> tuple[frozenset[str], frozenset[str]]:
    declarations: tuple[tuple[frozenset[str], frozenset[str]], ...] = tuple(
        _declarations(node=statement) for statement in node.body
    )
    return (
        frozenset(name for global_names, _ in declarations for name in global_names),
        frozenset(name for _, nonlocal_names in declarations for name in nonlocal_names),
    )


def _declarations(*, node: ast.AST) -> tuple[frozenset[str], frozenset[str]]:
    if isinstance(node, (*_function_nodes, ast.ClassDef)):
        return frozenset(), frozenset()
    if isinstance(node, ast.Global):
        return frozenset(node.names), frozenset()
    if isinstance(node, ast.Nonlocal):
        return frozenset(), frozenset(node.names)
    declarations: tuple[tuple[frozenset[str], frozenset[str]], ...] = tuple(
        _declarations(node=child) for child in ast.iter_child_nodes(node)
    )
    return (
        frozenset(name for global_names, _ in declarations for name in global_names),
        frozenset(name for _, nonlocal_names in declarations for name in nonlocal_names),
    )


def _scope_bindings(*, nodes: list[ast.stmt], include_imports: bool) -> frozenset[str]:
    return frozenset(
        name for node in nodes for name in _bindings(node=node, include_imports=include_imports)
    )


def _bindings(*, node: ast.AST, include_imports: bool) -> frozenset[str]:
    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
        return frozenset({node.name})
    if isinstance(node, (ast.Lambda, *_comprehension_nodes)):
        return frozenset()
    if isinstance(node, ast.Import):
        if not include_imports:
            return frozenset()
        return frozenset(
            alias.asname or alias.name.split(".", maxsplit=1)[0] for alias in node.names
        )
    if isinstance(node, ast.ImportFrom):
        if not include_imports:
            return frozenset()
        return frozenset(alias.asname or alias.name for alias in node.names if alias.name != "*")
    direct_names: frozenset[str] = frozenset(
        {node.name} if isinstance(node, ast.ExceptHandler) and node.name is not None else set()
    )
    if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store | ast.Del):
        direct_names = frozenset({node.id})
    return direct_names | frozenset(
        name
        for child in ast.iter_child_nodes(node)
        for name in _bindings(node=child, include_imports=include_imports)
    )


def _argument_names(*, arguments: ast.arguments) -> frozenset[str]:
    names: set[str] = {
        argument.arg
        for argument in (*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs)
    }
    if arguments.vararg is not None:
        names.add(arguments.vararg.arg)
    if arguments.kwarg is not None:
        names.add(arguments.kwarg.arg)
    return frozenset(names)


def _target_names(*, target: ast.expr) -> tuple[str, ...]:
    return tuple(node.id for node in ast.walk(target) if isinstance(node, ast.Name))


def _mutation_root_name(*, target: ast.expr) -> str | None:
    if isinstance(target, ast.Name):
        return target.id
    return _root_name(node=target)


def _root_name(*, node: ast.expr) -> str | None:
    current: ast.expr = node
    while isinstance(current, ast.Attribute | ast.Subscript):
        current = current.value
    return current.id if isinstance(current, ast.Name) else None
