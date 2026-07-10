"""Candidate-driven lexical analysis for outer-state mutations."""

from __future__ import annotations

import ast
from collections.abc import Mapping

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
_candidate_types: tuple[type[ast.AST], ...] = (
    ast.Assign,
    ast.AnnAssign,
    ast.AugAssign,
    ast.NamedExpr,
    ast.Delete,
    ast.Call,
)
_wildcard_import_name: str = "*"


def outer_state_mutation_nodes(
    *,
    module: ast.Module,
    node_index: Mapping[type[ast.AST], tuple[ast.AST, ...]],
    parent_by_node: Mapping[ast.AST, ast.AST],
) -> tuple[ast.AST, ...]:
    """Return indexed mutation candidates that resolve to an outer binding."""

    module_bindings: frozenset[str] = _scope_bindings(nodes=module.body, include_imports=False)
    binding_cache: dict[ast.AST, frozenset[str]] = {}
    declaration_cache: dict[ast.AST, tuple[frozenset[str], frozenset[str]]] = {}
    mutations: list[ast.AST] = []
    for candidate in _mutation_candidates(node_index=node_index):
        owner: ast.AST | None = _owning_function(node=candidate, parent_by_node=parent_by_node)
        if owner is None or not _inside_owned_body(
            node=candidate, owner=owner, parent_by_node=parent_by_node
        ):
            continue
        local_bindings, binding_cache, declaration_cache = _scope_local_bindings(
            owner=owner,
            binding_cache=binding_cache,
            declaration_cache=declaration_cache,
        )
        declarations, declaration_cache = _scope_declarations(
            owner=owner, declaration_cache=declaration_cache
        )
        global_names, nonlocal_names = declarations
        enclosing_bindings, binding_cache, declaration_cache = _enclosing_bindings(
            owner=owner,
            parent_by_node=parent_by_node,
            binding_cache=binding_cache,
            declaration_cache=declaration_cache,
        )
        mutation: ast.AST | None = _outer_mutation(
            node=candidate,
            local_bindings=local_bindings,
            outer_bindings=module_bindings | enclosing_bindings,
            global_names=global_names,
            nonlocal_names=nonlocal_names,
            shadowed_names=_comprehension_bindings(
                node=candidate, owner=owner, parent_by_node=parent_by_node
            ),
        )
        if mutation is not None:
            mutations.append(mutation)
    return tuple(mutations)


def _mutation_candidates(
    *, node_index: Mapping[type[ast.AST], tuple[ast.AST, ...]]
) -> tuple[ast.AST, ...]:
    candidates: list[ast.AST] = []
    for node_type in _candidate_types:
        for node in node_index.get(node_type, ()):
            if not isinstance(node, ast.Call) or _is_mutator_call(node):
                candidates.append(node)
    return tuple(candidates)


def _is_mutator_call(node: ast.Call) -> bool:
    return isinstance(node.func, ast.Attribute) and node.func.attr in _mutator_methods


def _owning_function(*, node: ast.AST, parent_by_node: Mapping[ast.AST, ast.AST]) -> ast.AST | None:
    current: ast.AST | None = parent_by_node.get(node)
    while current is not None:
        if isinstance(current, _function_nodes):
            return current
        if isinstance(current, ast.ClassDef):
            return None
        current = parent_by_node.get(current)
    return None


def _inside_owned_body(
    *, node: ast.AST, owner: ast.AST, parent_by_node: Mapping[ast.AST, ast.AST]
) -> bool:
    current: ast.AST = node
    parent: ast.AST | None = parent_by_node.get(current)
    while parent is not None and parent is not owner:
        current = parent
        parent = parent_by_node.get(current)
    if parent is not owner:
        return False
    if isinstance(owner, ast.Lambda):
        return current is owner.body
    if isinstance(owner, ast.FunctionDef | ast.AsyncFunctionDef):
        return any(current is statement for statement in owner.body)
    return False


def _scope_local_bindings(
    *,
    owner: ast.AST,
    binding_cache: dict[ast.AST, frozenset[str]],
    declaration_cache: dict[ast.AST, tuple[frozenset[str], frozenset[str]]],
) -> tuple[
    frozenset[str],
    dict[ast.AST, frozenset[str]],
    dict[ast.AST, tuple[frozenset[str], frozenset[str]]],
]:
    cached: frozenset[str] | None = binding_cache.get(owner)
    if cached is not None:
        return cached, binding_cache, declaration_cache
    if isinstance(owner, ast.Lambda):
        bindings: frozenset[str] = _argument_names(arguments=owner.args)
    elif isinstance(owner, ast.FunctionDef | ast.AsyncFunctionDef):
        declarations, declaration_cache = _scope_declarations(
            owner=owner, declaration_cache=declaration_cache
        )
        global_names, nonlocal_names = declarations
        bindings = (
            (
                _argument_names(arguments=owner.args)
                | _scope_bindings(nodes=owner.body, include_imports=True)
            )
            - global_names
            - nonlocal_names
        )
    else:
        bindings = frozenset()
    binding_cache[owner] = bindings
    return bindings, binding_cache, declaration_cache


def _scope_declarations(
    *,
    owner: ast.AST,
    declaration_cache: dict[ast.AST, tuple[frozenset[str], frozenset[str]]],
) -> tuple[
    tuple[frozenset[str], frozenset[str]],
    dict[ast.AST, tuple[frozenset[str], frozenset[str]]],
]:
    cached: tuple[frozenset[str], frozenset[str]] | None = declaration_cache.get(owner)
    if cached is not None:
        return cached, declaration_cache
    if isinstance(owner, ast.FunctionDef | ast.AsyncFunctionDef):
        declarations: tuple[tuple[frozenset[str], frozenset[str]], ...] = tuple(
            _declarations(node=statement) for statement in owner.body
        )
        result: tuple[frozenset[str], frozenset[str]] = _merge_declarations(
            declarations=declarations
        )
    else:
        result = (frozenset(), frozenset())
    declaration_cache[owner] = result
    return result, declaration_cache


def _enclosing_bindings(
    *,
    owner: ast.AST,
    parent_by_node: Mapping[ast.AST, ast.AST],
    binding_cache: dict[ast.AST, frozenset[str]],
    declaration_cache: dict[ast.AST, tuple[frozenset[str], frozenset[str]]],
) -> tuple[
    frozenset[str],
    dict[ast.AST, frozenset[str]],
    dict[ast.AST, tuple[frozenset[str], frozenset[str]]],
]:
    bindings: set[str] = set()
    current: ast.AST | None = parent_by_node.get(owner)
    while current is not None:
        if isinstance(current, _function_nodes):
            scope_bindings, binding_cache, declaration_cache = _scope_local_bindings(
                owner=current,
                binding_cache=binding_cache,
                declaration_cache=declaration_cache,
            )
            bindings.update(scope_bindings)
        current = parent_by_node.get(current)
    return frozenset(bindings), binding_cache, declaration_cache


def _comprehension_bindings(
    *, node: ast.AST, owner: ast.AST, parent_by_node: Mapping[ast.AST, ast.AST]
) -> frozenset[str]:
    bindings: set[str] = set()
    current: ast.AST | None = parent_by_node.get(node)
    while current is not None and current is not owner:
        if isinstance(current, ast.DictComp | ast.GeneratorExp | ast.ListComp | ast.SetComp):
            for generator in current.generators:
                bindings.update(_target_names(target=generator.target))
        current = parent_by_node.get(current)
    return frozenset(bindings)


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
    return _merge_declarations(declarations=declarations)


def _scope_bindings(*, nodes: list[ast.stmt], include_imports: bool) -> frozenset[str]:
    names: set[str] = set()
    for node in nodes:
        names.update(_bindings(node=node, include_imports=include_imports))
    return frozenset(names)


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
        return frozenset(
            alias.asname or alias.name
            for alias in node.names
            if alias.name != _wildcard_import_name
        )
    direct_names: frozenset[str] = frozenset(
        {node.name} if isinstance(node, ast.ExceptHandler) and node.name is not None else set()
    )
    if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store | ast.Del):
        direct_names = frozenset({node.id})
    descendant_names: set[str] = set()
    for child in ast.iter_child_nodes(node):
        descendant_names.update(_bindings(node=child, include_imports=include_imports))
    return direct_names | frozenset(descendant_names)


def _merge_declarations(
    *, declarations: tuple[tuple[frozenset[str], frozenset[str]], ...]
) -> tuple[frozenset[str], frozenset[str]]:
    global_names: set[str] = set()
    nonlocal_names: set[str] = set()
    for declared_globals, declared_nonlocals in declarations:
        global_names.update(declared_globals)
        nonlocal_names.update(declared_nonlocals)
    return frozenset(global_names), frozenset(nonlocal_names)


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
