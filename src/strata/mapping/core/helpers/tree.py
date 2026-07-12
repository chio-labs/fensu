"""Resolve project-local calls into a recursive call tree."""

from __future__ import annotations

import ast

from strata.mapping.core.constants import (
    CLASS_RECEIVER_NAME,
    METHOD_RECEIVER_NAMES,
    SELF_RECEIVER_NAME,
)
from strata.mapping.core.models import (
    CallMapNode,
    ClassDefinition,
    ClassReference,
    FunctionDefinition,
    ImportView,
    ProjectIndex,
    ResolvedCallable,
    UnresolvedCall,
)


def build_tree(*, root: FunctionDefinition, index: ProjectIndex, depth: int) -> CallMapNode:
    """Build a depth-bounded downstream tree with branch-local cycle detection."""

    dispatch_class_key: str | None = None
    if root.owning_class is not None:
        dispatch_class_key = ClassDefinition.build_key(
            module_name=root.module_name, name=root.owning_class
        )
    return _build_node(
        definition=root,
        dispatch_class_key=dispatch_class_key,
        index=index,
        remaining_depth=depth,
        ancestors=frozenset(),
        method_cache={},
    )


def _build_node(
    *,
    definition: FunctionDefinition,
    dispatch_class_key: str | None,
    index: ProjectIndex,
    remaining_depth: int,
    ancestors: frozenset[tuple[str, str | None]],
    method_cache: dict[tuple[str, str], FunctionDefinition | None],
) -> CallMapNode:
    key: tuple[str, str | None] = (definition.key, dispatch_class_key)
    dispatch_class_name: str | None = _dispatch_class_name(
        definition=definition,
        dispatch_class_key=dispatch_class_key,
        index=index,
    )
    if key in ancestors:
        return CallMapNode(
            definition=definition,
            entries=(),
            dispatch_class_name=dispatch_class_name,
            cycle=True,
        )
    call_entries: tuple[ResolvedCallable | UnresolvedCall, ...] = _call_entries(
        definition=definition,
        dispatch_class_key=dispatch_class_key,
        index=index,
        method_cache=method_cache,
    )
    if remaining_depth == 0:
        return CallMapNode(
            definition=definition,
            entries=(),
            dispatch_class_name=dispatch_class_name,
            truncated=bool(call_entries),
        )
    next_ancestors: frozenset[tuple[str, str | None]] = ancestors | {key}
    entries: tuple[CallMapNode | UnresolvedCall, ...] = tuple(
        entry
        if isinstance(entry, UnresolvedCall)
        else _build_node(
            definition=entry.definition,
            dispatch_class_key=entry.dispatch_class_key,
            index=index,
            remaining_depth=remaining_depth - 1,
            ancestors=next_ancestors,
            method_cache=method_cache,
        )
        for entry in call_entries
    )
    return CallMapNode(
        definition=definition,
        entries=entries,
        dispatch_class_name=dispatch_class_name,
    )


def _call_entries(
    *,
    definition: FunctionDefinition,
    dispatch_class_key: str | None,
    index: ProjectIndex,
    method_cache: dict[tuple[str, str], FunctionDefinition | None],
) -> tuple[ResolvedCallable | UnresolvedCall, ...]:
    entries: list[ResolvedCallable | UnresolvedCall] = []
    seen: set[tuple[str, str | None]] = set()
    parameter_names: frozenset[str] = _parameter_names(definition.node)
    untyped_parameters: frozenset[str] = _untyped_parameter_names(definition.node)
    receiver_states: dict[ast.Call, dict[str, str | None]] = _receiver_states(
        definition=definition,
        dispatch_class_key=dispatch_class_key,
        index=index,
        method_cache=method_cache,
    )
    for call in _owned_calls(definition.node):
        local_types: dict[str, str | None] = receiver_states.get(call, {})
        if isinstance(call.func, ast.Name) and call.func.id in parameter_names:
            entries.append(
                UnresolvedCall(name=call.func.id, line=call.lineno, reason="parameter call")
            )
            continue
        target, unresolved = _resolve_call(
            call=call,
            definition=definition,
            dispatch_class_key=dispatch_class_key,
            index=index,
            local_types=local_types,
            untyped_parameters=untyped_parameters,
            method_cache=method_cache,
        )
        if unresolved is not None:
            entries.append(unresolved)
        if target is None:
            continue
        target_key: tuple[str, str | None] = (
            target.definition.key,
            target.dispatch_class_key,
        )
        if target_key in seen:
            continue
        seen.add(target_key)
        entries.append(target)
    return tuple(entries)


def _resolve_call(
    *,
    call: ast.Call,
    definition: FunctionDefinition,
    dispatch_class_key: str | None,
    index: ProjectIndex,
    local_types: dict[str, str | None],
    untyped_parameters: frozenset[str],
    method_cache: dict[tuple[str, str], FunctionDefinition | None],
) -> tuple[ResolvedCallable | None, UnresolvedCall | None]:
    if isinstance(call.func, ast.Name):
        if call.func.id in local_types:
            return None, None
        key: str | None = _top_level_call_key(call=call.func, definition=definition)
        target: FunctionDefinition | None = index.functions.get(key) if key is not None else None
        return ResolvedCallable(target) if target is not None else None, None
    if not isinstance(call.func, ast.Attribute):
        return None, None
    receiver: ast.expr = call.func.value
    receiver_class, project_owned = _receiver_class(
        expression=receiver,
        definition=definition,
        dispatch_class_key=dispatch_class_key,
        index=index,
        local_types=local_types,
        method_cache=method_cache,
    )
    if receiver_class is not None:
        if receiver_class.protocol:
            return None, _unresolved(call, reason="protocol dispatch")
        target: FunctionDefinition | None = _method_definition(
            class_definition=receiver_class,
            method_name=call.func.attr,
            index=index,
            cache=method_cache,
            active=frozenset(),
        )
        if target is not None:
            return ResolvedCallable(target, dispatch_class_key=receiver_class.key), None
        reason: str = "self method" if _is_direct_self_receiver(receiver) else "dynamic attribute"
        return None, _unresolved(call, reason=reason)
    root_name: str | None = _root_name(receiver)
    if root_name in untyped_parameters:
        return None, _unresolved(call, reason="parameter method")
    if _is_direct_self_receiver(receiver):
        return None, _unresolved(call, reason="self method")
    if project_owned:
        return None, _unresolved(call, reason="dynamic attribute")
    if root_name is not None and root_name in local_types:
        return None, None
    key = _imported_module_call_key(call=call.func, definition=definition)
    target = index.functions.get(key) if key is not None else None
    return ResolvedCallable(target) if target is not None else None, None


def _receiver_class(
    *,
    expression: ast.expr,
    definition: FunctionDefinition,
    dispatch_class_key: str | None,
    index: ProjectIndex,
    local_types: dict[str, str | None],
    method_cache: dict[tuple[str, str], FunctionDefinition | None],
) -> tuple[ClassDefinition | None, bool]:
    if isinstance(expression, ast.Name):
        if expression.id in METHOD_RECEIVER_NAMES and definition.owning_class is not None:
            class_key: str = dispatch_class_key or ClassDefinition.build_key(
                module_name=definition.module_name,
                name=definition.owning_class,
            )
            return index.classes.get(class_key), True
        if expression.id in local_types:
            local_key: str | None = local_types[expression.id]
            return (index.classes.get(local_key), True) if local_key is not None else (None, False)
        direct_class: ClassDefinition | None = _resolve_class_expression(
            expression=expression, definition=definition, index=index
        )
        return (direct_class, True) if direct_class is not None else (None, False)
    direct_class = None
    root_name: str | None = _root_name(expression)
    if root_name is None or root_name not in local_types:
        direct_class = _resolve_class_expression(
            expression=expression, definition=definition, index=index
        )
    if direct_class is not None:
        return direct_class, True
    if isinstance(expression, ast.Call):
        constructor: ClassDefinition | None = None
        constructor_root: str | None = _root_name(expression.func)
        if constructor_root is None or constructor_root not in local_types:
            constructor = _resolve_class_expression(
                expression=expression.func, definition=definition, index=index
            )
        if constructor is not None:
            return constructor, True
        factory: FunctionDefinition | None = _called_function(
            call=expression,
            definition=definition,
            dispatch_class_key=dispatch_class_key,
            index=index,
            local_types=local_types,
            method_cache=method_cache,
        )
        if factory is None or factory.node.returns is None:
            return None, factory is not None
        returned: ClassDefinition | None = _resolve_class_expression(
            expression=factory.node.returns,
            definition=factory,
            index=index,
            annotation=True,
        )
        return returned, returned is not None
    if isinstance(expression, ast.Attribute):
        owner, project_owned = _receiver_class(
            expression=expression.value,
            definition=definition,
            dispatch_class_key=dispatch_class_key,
            index=index,
            local_types=local_types,
            method_cache=method_cache,
        )
        if owner is None:
            return None, project_owned
        reference: ClassReference | None = owner.instance_attributes.get(expression.attr)
        if reference is None:
            reference = owner.class_attributes.get(expression.attr)
        if reference is None:
            return None, True
        attribute_class: ClassDefinition | None = _resolve_class_expression(
            expression=reference.expression,
            definition=owner,
            index=index,
            annotation=reference.annotation,
        )
        return attribute_class, attribute_class is not None
    return None, False


def _called_function(
    *,
    call: ast.Call,
    definition: FunctionDefinition,
    dispatch_class_key: str | None,
    index: ProjectIndex,
    local_types: dict[str, str | None],
    method_cache: dict[tuple[str, str], FunctionDefinition | None],
) -> FunctionDefinition | None:
    if isinstance(call.func, ast.Name):
        if call.func.id in local_types:
            return None
        key: str | None = _top_level_call_key(call=call.func, definition=definition)
        return index.functions.get(key) if key is not None else None
    if not isinstance(call.func, ast.Attribute):
        return None
    receiver, _ = _receiver_class(
        expression=call.func.value,
        definition=definition,
        dispatch_class_key=dispatch_class_key,
        index=index,
        local_types=local_types,
        method_cache=method_cache,
    )
    if receiver is not None:
        return _method_definition(
            class_definition=receiver,
            method_name=call.func.attr,
            index=index,
            cache=method_cache,
            active=frozenset(),
        )
    root_name: str | None = _root_name(call.func.value)
    if root_name is not None and root_name in local_types:
        return None
    key = _imported_module_call_key(call=call.func, definition=definition)
    return index.functions.get(key) if key is not None else None


def _method_definition(
    *,
    class_definition: ClassDefinition,
    method_name: str,
    index: ProjectIndex,
    cache: dict[tuple[str, str], FunctionDefinition | None],
    active: frozenset[tuple[str, str]],
) -> FunctionDefinition | None:
    lookup_key: tuple[str, str] = (class_definition.key, method_name)
    if lookup_key in cache:
        return cache[lookup_key]
    if lookup_key in active:
        return None
    direct_key: str = FunctionDefinition.build_key(
        module_name=class_definition.module_name,
        name=method_name,
        owning_class=class_definition.name,
    )
    direct: FunctionDefinition | None = index.functions.get(direct_key)
    if direct is not None:
        cache[lookup_key] = direct
        return direct
    candidates: dict[str, FunctionDefinition] = {}
    next_active: frozenset[tuple[str, str]] = active | {lookup_key}
    for base in class_definition.bases:
        base_class: ClassDefinition | None = _resolve_class_expression(
            expression=base,
            definition=class_definition,
            index=index,
        )
        if base_class is None:
            continue
        inherited: FunctionDefinition | None = _method_definition(
            class_definition=base_class,
            method_name=method_name,
            index=index,
            cache=cache,
            active=next_active,
        )
        if inherited is not None:
            candidates[inherited.key] = inherited
    if len(candidates) == 1:
        result: FunctionDefinition | None = next(iter(candidates.values()))
    else:
        result = None
    cache[lookup_key] = result
    return result


def _resolve_class_expression(
    *,
    expression: ast.expr,
    definition: FunctionDefinition | ClassDefinition,
    index: ProjectIndex,
    annotation: bool = False,
) -> ClassDefinition | None:
    if isinstance(expression, ast.Subscript):
        return _resolve_class_expression(
            expression=expression.value,
            definition=definition,
            index=index,
            annotation=annotation,
        )
    if isinstance(expression, ast.Constant) and isinstance(expression.value, str):
        try:
            parsed: ast.expr = ast.parse(expression.value, mode="eval").body
        except SyntaxError:
            return None
        return _resolve_class_expression(
            expression=parsed,
            definition=definition,
            index=index,
            annotation=annotation,
        )
    imports: ImportView = (
        definition.imports.annotation if annotation else definition.imports.runtime
    )
    if isinstance(expression, ast.Name):
        local: ClassDefinition | None = index.classes.get(
            ClassDefinition.build_key(module_name=definition.module_name, name=expression.id)
        )
        if local is not None:
            return local
        imported: tuple[str, str] | None = imports.symbols.get(expression.id)
        if imported is not None:
            imported_key: str = ClassDefinition.build_key(module_name=imported[0], name=imported[1])
            return index.classes.get(imported_key)
        return None
    if isinstance(expression, ast.Attribute):
        spelling: str = _expression_name(expression)
        first, separator, remainder = spelling.partition(".")
        imported_module: str | None = imports.modules.get(first)
        if separator and imported_module is not None:
            spelling = f"{imported_module}.{remainder}"
        return index.classes.get(spelling)
    return None


def _receiver_states(
    *,
    definition: FunctionDefinition,
    dispatch_class_key: str | None,
    index: ProjectIndex,
    method_cache: dict[tuple[str, str], FunctionDefinition | None],
) -> dict[ast.Call, dict[str, str | None]]:
    bindings: dict[str, str | None] = {name: None for name in _parameter_names(definition.node)}
    invalid: set[str] = set()
    for argument in _arguments(definition.node):
        if argument.annotation is None:
            continue
        class_definition: ClassDefinition | None = _resolve_class_expression(
            expression=argument.annotation,
            definition=definition,
            index=index,
            annotation=True,
        )
        if class_definition is not None:
            bindings[argument.arg] = class_definition.key
    states: dict[ast.Call, dict[str, str | None]] = {
        call: dict(bindings) for call in _owned_calls(definition.node)
    }
    for statement in definition.node.body:
        statement_calls: tuple[ast.Call, ...] = _statement_calls(statement)
        if _is_control_flow(statement):
            assigned_names: frozenset[str] = _assigned_names(statement)
            statement_state: dict[str, str | None] = dict(bindings)
            for name in assigned_names:
                statement_state[name] = None
            for call in statement_calls:
                states[call] = statement_state
            invalid.update(assigned_names)
            for name in assigned_names:
                bindings[name] = None
            continue
        for call in statement_calls:
            states[call] = dict(bindings)
        name, class_definition = _local_binding(
            statement=statement,
            definition=definition,
            dispatch_class_key=dispatch_class_key,
            index=index,
            bindings=bindings,
            method_cache=method_cache,
        )
        if name is None:
            assigned_names = _assigned_names(statement)
            invalid.update(assigned_names)
            for assigned_name in assigned_names:
                bindings[assigned_name] = None
            continue
        if class_definition is None:
            invalid.add(name)
            bindings[name] = None
            continue
        if name in invalid or (name in bindings and bindings[name] != class_definition.key):
            invalid.add(name)
            bindings[name] = None
        else:
            bindings[name] = class_definition.key
    return states


def _local_binding(
    *,
    statement: ast.stmt,
    definition: FunctionDefinition,
    dispatch_class_key: str | None,
    index: ProjectIndex,
    bindings: dict[str, str | None],
    method_cache: dict[tuple[str, str], FunctionDefinition | None],
) -> tuple[str | None, ClassDefinition | None]:
    if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
        return statement.target.id, _resolve_class_expression(
            expression=statement.annotation,
            definition=definition,
            index=index,
            annotation=True,
        )
    if isinstance(statement, ast.Assign) and len(statement.targets) == 1:
        target: ast.expr = statement.targets[0]
        if not isinstance(target, ast.Name):
            return None, None
        if isinstance(statement.value, ast.Call):
            constructor: ClassDefinition | None = None
            constructor_root: str | None = _root_name(statement.value.func)
            if constructor_root is None or constructor_root not in bindings:
                constructor = _resolve_class_expression(
                    expression=statement.value.func,
                    definition=definition,
                    index=index,
                )
            if constructor is not None:
                return target.id, constructor
            factory: FunctionDefinition | None = _called_function(
                call=statement.value,
                definition=definition,
                dispatch_class_key=dispatch_class_key,
                index=index,
                local_types=bindings,
                method_cache=method_cache,
            )
            if factory is None or factory.node.returns is None:
                return target.id, None
            return target.id, _resolve_class_expression(
                expression=factory.node.returns,
                definition=factory,
                index=index,
                annotation=True,
            )
        if isinstance(statement.value, ast.Name):
            alias_key: str | None = bindings.get(statement.value.id)
            return target.id, index.classes.get(alias_key) if alias_key is not None else None
        return target.id, None
    if isinstance(statement, ast.AugAssign) and isinstance(statement.target, ast.Name):
        return statement.target.id, None
    return None, None


def _statement_calls(statement: ast.stmt) -> tuple[ast.Call, ...]:
    if isinstance(statement, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
        return ()
    return _owned_calls(statement)


def _is_control_flow(statement: ast.stmt) -> bool:
    return isinstance(
        statement,
        ast.If
        | ast.For
        | ast.AsyncFor
        | ast.While
        | ast.Try
        | ast.TryStar
        | ast.With
        | ast.AsyncWith
        | ast.Match,
    )


def _assigned_names(node: ast.AST) -> frozenset[str]:
    return frozenset(_collect_assigned_names(node=node, nested=False))


def _dispatch_class_name(
    *, definition: FunctionDefinition, dispatch_class_key: str | None, index: ProjectIndex
) -> str | None:
    if definition.owning_class is None or dispatch_class_key is None:
        return None
    dispatch_class: ClassDefinition | None = index.classes.get(dispatch_class_key)
    if dispatch_class is None or dispatch_class.name == definition.owning_class:
        return None
    return dispatch_class.name


def _collect_assigned_names(*, node: ast.AST, nested: bool) -> set[str]:
    names: set[str] = set()
    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
        if nested:
            names.add(node.name)
            return names
    elif isinstance(node, ast.Lambda):
        return names
    elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store | ast.Del):
        names.add(node.id)
    elif isinstance(node, ast.Import | ast.ImportFrom):
        for alias in node.names:
            names.add(alias.asname or alias.name.split(".", maxsplit=1)[0])
    elif isinstance(node, ast.ExceptHandler) and node.name is not None:
        names.add(node.name)
    elif isinstance(node, ast.MatchAs) and node.name is not None:
        names.add(node.name)
    elif isinstance(node, ast.MatchStar) and node.name is not None:
        names.add(node.name)
    elif isinstance(node, ast.MatchMapping) and node.rest is not None:
        names.add(node.rest)
    for child in ast.iter_child_nodes(node):
        names.update(_collect_assigned_names(node=child, nested=True))
    return names


def _top_level_call_key(*, call: ast.Name, definition: FunctionDefinition) -> str:
    imported: tuple[str, str] | None = definition.imports.runtime.symbols.get(call.id)
    if imported is not None:
        return FunctionDefinition.build_key(module_name=imported[0], name=imported[1])
    return FunctionDefinition.build_key(module_name=definition.module_name, name=call.id)


def _imported_module_call_key(*, call: ast.Attribute, definition: FunctionDefinition) -> str | None:
    if not isinstance(call.value, ast.Name):
        return None
    imported_module: str | None = definition.imports.runtime.modules.get(call.value.id)
    if imported_module is None:
        return None
    return FunctionDefinition.build_key(module_name=imported_module, name=call.attr)


def _unresolved(call: ast.Call, *, reason: str) -> UnresolvedCall:
    return UnresolvedCall(name=ast.unparse(call.func), line=call.lineno, reason=reason)


def _is_direct_self_receiver(expression: ast.expr) -> bool:
    return isinstance(expression, ast.Name) and expression.id in METHOD_RECEIVER_NAMES


def _expression_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix: str = _expression_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


def _root_name(node: ast.expr) -> str | None:
    while isinstance(node, ast.Attribute):
        node = node.value
    return node.id if isinstance(node, ast.Name) else None


def _owned_calls(node: ast.AST) -> tuple[ast.Call, ...]:
    calls: list[ast.Call] = []
    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef | ast.Lambda):
            continue
        if isinstance(child, ast.Call):
            calls.append(child)
        calls.extend(_owned_calls(child))
    return tuple(calls)


def _arguments(node: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[ast.arg, ...]:
    arguments: ast.arguments = node.args
    positional: tuple[ast.arg, ...] = (*arguments.posonlyargs, *arguments.args)
    return (*positional, *arguments.kwonlyargs)


def _parameter_names(node: ast.FunctionDef | ast.AsyncFunctionDef) -> frozenset[str]:
    arguments: ast.arguments = node.args
    names: set[str] = {argument.arg for argument in _arguments(node)}
    if arguments.vararg is not None:
        names.add(arguments.vararg.arg)
    if arguments.kwarg is not None:
        names.add(arguments.kwarg.arg)
    return frozenset(names)


def _untyped_parameter_names(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> frozenset[str]:
    names: set[str] = {argument.arg for argument in _arguments(node) if argument.annotation is None}
    if node.args.vararg is not None and node.args.vararg.annotation is None:
        names.add(node.args.vararg.arg)
    if node.args.kwarg is not None and node.args.kwarg.annotation is None:
        names.add(node.args.kwarg.arg)
    names.discard(SELF_RECEIVER_NAME)
    names.discard(CLASS_RECEIVER_NAME)
    return frozenset(names)
