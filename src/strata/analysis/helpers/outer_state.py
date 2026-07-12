"""Candidate-driven lexical analysis for outer-state mutations."""

from __future__ import annotations

import ast
from collections import deque
from collections.abc import Mapping
from pathlib import Path

from strata.analysis.helpers.locations import source_location
from strata.analysis.models import ParameterMutationFact

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
_exempt_parameters: frozenset[str] = frozenset({"cls", "self"})


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
    enclosing_cache: dict[ast.AST, frozenset[str]] = {}
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
        enclosing_bindings, binding_cache, declaration_cache, enclosing_cache = _enclosing_bindings(
            owner=owner,
            parent_by_node=parent_by_node,
            binding_cache=binding_cache,
            declaration_cache=declaration_cache,
            enclosing_cache=enclosing_cache,
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


def parameter_mutation_facts(
    *,
    path: Path,
    nodes: tuple[ast.AST, ...],
    node_index: Mapping[type[ast.AST], tuple[ast.AST, ...]],
    parent_by_node: Mapping[ast.AST, ast.AST],
) -> tuple[ParameterMutationFact, ...]:
    """Return first direct mutation metadata for each function parameter in AST BFS order."""

    function_nodes: tuple[ast.AST, ...] = (
        *node_index.get(ast.FunctionDef, ()),
        *node_index.get(ast.AsyncFunctionDef, ()),
    )
    parameters_by_function: dict[ast.AST, frozenset[str]] = {
        node: _parameter_names(node)
        for node in function_nodes
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    }
    if not parameters_by_function:
        return ()
    candidates: frozenset[ast.AST] = _parameter_mutation_candidates(node_index=node_index)
    mutations_by_function: dict[ast.AST, dict[str, ast.AST]] = {}
    for node in nodes:
        if node not in candidates:
            continue
        root_names: tuple[str, ...] = _parameter_mutation_root_names(node)
        if not root_names:
            continue
        current: ast.AST | None = parent_by_node.get(node)
        while current is not None:
            parameter_names: frozenset[str] | None = parameters_by_function.get(current)
            if parameter_names is not None:
                mutated_name: str | None = next(
                    (name for name in root_names if name in parameter_names), None
                )
                if mutated_name is not None:
                    mutations_by_function.setdefault(current, {}).setdefault(mutated_name, node)
            current = parent_by_node.get(current)
    returned_by_function: dict[ast.AST, set[str]] = {node: set() for node in mutations_by_function}
    for node in node_index.get(ast.Return, ()):
        if not isinstance(node, ast.Return) or node.value is None:
            continue
        returned_names: frozenset[str] = frozenset(
            child.id for child in ast.walk(node.value) if isinstance(child, ast.Name)
        )
        current = parent_by_node.get(node)
        while current is not None:
            if current in returned_by_function:
                returned_by_function[current].update(returned_names)
            current = parent_by_node.get(current)
    facts: list[ParameterMutationFact] = []
    for node in function_nodes:
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        function_returned_names: set[str] = returned_by_function.get(node, set())
        for parameter_name, mutation in mutations_by_function.get(node, {}).items():
            facts.append(
                ParameterMutationFact(
                    function_name=node.name,
                    parameter_name=parameter_name,
                    location=source_location(path=path, node=mutation),
                    returned=parameter_name in function_returned_names,
                    dunder=node.name.startswith("__") and node.name.endswith("__"),
                    setter=any(
                        _decorator_name(decorator).endswith(".setter")
                        for decorator in node.decorator_list
                    ),
                )
            )
    return tuple(facts)


def _parameter_mutation_candidates(
    *, node_index: Mapping[type[ast.AST], tuple[ast.AST, ...]]
) -> frozenset[ast.AST]:
    candidates: set[ast.AST] = set()
    for node_type in (ast.Assign, ast.AnnAssign, ast.AugAssign):
        candidates.update(node_index.get(node_type, ()))
    for node in node_index.get(ast.Call, ()):
        if isinstance(node, ast.Call) and _is_mutator_call(node):
            candidates.add(node)
    return frozenset(candidates)


def _parameter_mutation_root_names(node: ast.AST) -> tuple[str, ...]:
    targets: tuple[ast.expr, ...] = ()
    if isinstance(node, ast.Assign):
        targets = tuple(node.targets)
    elif isinstance(node, ast.AnnAssign | ast.AugAssign):
        targets = (node.target,)
    elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        targets = (node.func.value,)
    names: list[str] = []
    for target in targets:
        if isinstance(target, ast.Name) and not isinstance(node, ast.Call):
            continue
        root_name: str | None = _root_name(node=target)
        if root_name is not None:
            names.append(root_name)
    return tuple(names)


def _parameter_names(node: ast.FunctionDef | ast.AsyncFunctionDef) -> frozenset[str]:
    names: set[str] = set(_argument_names(arguments=node.args)) - _exempt_parameters
    return frozenset(names)


def _decorator_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent: str = _decorator_name(node.value)
        return node.attr if not parent else f"{parent}.{node.attr}"
    if isinstance(node, ast.Call):
        return _decorator_name(node.func)
    return ""


def _mutation_candidates(
    *, node_index: Mapping[type[ast.AST], tuple[ast.AST, ...]]
) -> tuple[ast.AST, ...]:
    candidates: list[ast.AST] = []
    declarations_present: bool = bool(
        node_index.get(ast.Global, ()) or node_index.get(ast.Nonlocal, ())
    )
    for node_type in _candidate_types:
        for node in node_index.get(node_type, ()):
            if isinstance(node, ast.Call) and not _is_mutator_call(node):
                continue
            if declarations_present or _can_mutate_outer_without_declaration(node):
                candidates.append(node)
    return tuple(candidates)


def _is_mutator_call(node: ast.Call) -> bool:
    return isinstance(node.func, ast.Attribute) and node.func.attr in _mutator_methods


def _can_mutate_outer_without_declaration(node: ast.AST) -> bool:
    if isinstance(node, ast.Call):
        return True
    return any(not isinstance(target, ast.Name) for target in _mutation_targets(node))


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
        scope_bindings, global_names, nonlocal_names = _scope_metadata(
            nodes=owner.body, include_imports=True
        )
        bindings = (
            (_argument_names(arguments=owner.args) | scope_bindings) - global_names - nonlocal_names
        )
        declaration_cache[owner] = (global_names, nonlocal_names)
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
        _, global_names, nonlocal_names = _scope_metadata(nodes=owner.body, include_imports=True)
        result: tuple[frozenset[str], frozenset[str]] = (global_names, nonlocal_names)
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
    enclosing_cache: dict[ast.AST, frozenset[str]],
) -> tuple[
    frozenset[str],
    dict[ast.AST, frozenset[str]],
    dict[ast.AST, tuple[frozenset[str], frozenset[str]]],
    dict[ast.AST, frozenset[str]],
]:
    cached: frozenset[str] | None = enclosing_cache.get(owner)
    if cached is not None:
        return cached, binding_cache, declaration_cache, enclosing_cache
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
    result: frozenset[str] = frozenset(bindings)
    enclosing_cache[owner] = result
    return result, binding_cache, declaration_cache, enclosing_cache


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
    targets: tuple[ast.expr, ...] = _mutation_targets(node)
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


def _mutation_targets(node: ast.AST) -> tuple[ast.expr, ...]:
    if isinstance(node, ast.Assign):
        return tuple(node.targets)
    if isinstance(node, ast.AnnAssign | ast.AugAssign | ast.NamedExpr):
        return (node.target,)
    if isinstance(node, ast.Delete):
        return tuple(node.targets)
    return ()


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


def _scope_bindings(*, nodes: list[ast.stmt], include_imports: bool) -> frozenset[str]:
    bindings, _, _ = _scope_metadata(nodes=nodes, include_imports=include_imports)
    return bindings


def _scope_metadata(
    *, nodes: list[ast.stmt], include_imports: bool
) -> tuple[frozenset[str], frozenset[str], frozenset[str]]:
    bindings: set[str] = set()
    global_names: set[str] = set()
    nonlocal_names: set[str] = set()
    pending: deque[ast.AST] = deque(nodes)
    while pending:
        node: ast.AST = pending.popleft()
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            bindings.add(node.name)
            continue
        if isinstance(node, (ast.Lambda, *_comprehension_nodes)):
            continue
        if isinstance(node, ast.Global):
            global_names.update(node.names)
        elif isinstance(node, ast.Nonlocal):
            nonlocal_names.update(node.names)
        elif isinstance(node, ast.Import) and include_imports:
            bindings.update(
                alias.asname or alias.name.split(".", maxsplit=1)[0] for alias in node.names
            )
        elif isinstance(node, ast.ImportFrom) and include_imports:
            bindings.update(
                alias.asname or alias.name
                for alias in node.names
                if alias.name != _wildcard_import_name
            )
        elif isinstance(node, ast.ExceptHandler) and node.name is not None:
            bindings.add(node.name)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store | ast.Del):
            bindings.add(node.id)
        pending.extend(ast.iter_child_nodes(node))
    return frozenset(bindings), frozenset(global_names), frozenset(nonlocal_names)


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
