"""Resolve project-local calls into a recursive call tree."""

from __future__ import annotations

from fensu.mapping.constants import (
    CLASS_RECEIVER_NAME,
    MAPPING_EXPRESSION_ATTRIBUTE,
    MAPPING_EXPRESSION_CALL,
    MAPPING_EXPRESSION_NAME,
    MAPPING_EXPRESSION_STRING,
    MAPPING_EXPRESSION_SUBSCRIPT,
    METHOD_RECEIVER_NAMES,
    SELF_RECEIVER_NAME,
    SUBSCRIPT_OPEN,
)
from fensu.mapping.models import (
    CallMapNode,
    ClassDefinition,
    ClassReference,
    FunctionDefinition,
    ImportView,
    MappingCall,
    MappingExpression,
    MappingStatement,
    ResolvedCallable,
    UnresolvedCall,
)
from fensu.mapping.types import SymbolResolver


def build_tree(*, root: FunctionDefinition, index: SymbolResolver, depth: int) -> CallMapNode:
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
    index: SymbolResolver,
    remaining_depth: int,
    ancestors: frozenset[tuple[str, str | None]],
    method_cache: dict[tuple[str, str, bool], FunctionDefinition | None],
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
    index: SymbolResolver,
    method_cache: dict[tuple[str, str, bool], FunctionDefinition | None],
) -> tuple[ResolvedCallable | UnresolvedCall, ...]:
    entries: list[ResolvedCallable | UnresolvedCall] = []
    seen: set[tuple[str, str | None]] = set()
    parameter_names: frozenset[str] = _parameter_names(definition)
    untyped_parameters: frozenset[str] = _untyped_parameter_names(definition)
    receiver_states: dict[MappingCall, dict[str, str | None]] = _receiver_states(
        definition=definition,
        dispatch_class_key=dispatch_class_key,
        index=index,
        method_cache=method_cache,
    )
    for call in definition.syntax.calls:
        local_types: dict[str, str | None] = receiver_states.get(call, {})
        if call.callee.kind == MAPPING_EXPRESSION_NAME and call.callee.name in parameter_names:
            entries.append(
                UnresolvedCall(name=call.callee.name, line=call.line, reason="parameter call")
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
    call: MappingCall,
    definition: FunctionDefinition,
    dispatch_class_key: str | None,
    index: SymbolResolver,
    local_types: dict[str, str | None],
    untyped_parameters: frozenset[str],
    method_cache: dict[tuple[str, str, bool], FunctionDefinition | None],
) -> tuple[ResolvedCallable | None, UnresolvedCall | None]:
    callee: MappingExpression = call.callee
    if callee.kind == MAPPING_EXPRESSION_NAME:
        if callee.name in local_types:
            return None, None
        key: str | None = _top_level_call_key(call=callee, definition=definition)
        target: FunctionDefinition | None = index.get_function(key) if key is not None else None
        return ResolvedCallable(target) if target is not None else None, None
    if callee.kind != MAPPING_EXPRESSION_ATTRIBUTE or callee.child is None:
        return None, None
    receiver: MappingExpression = callee.child
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
            candidates: dict[tuple[str, str], ResolvedCallable] = {}
            for implementation in index.get_protocol_implementations(receiver_class.key):
                implementation_method: FunctionDefinition | None = _method_definition(
                    class_definition=implementation,
                    method_name=callee.name,
                    index=index,
                    cache=method_cache,
                    active=frozenset(),
                    exclude_protocol_bases=True,
                )
                if implementation_method is not None:
                    candidate: ResolvedCallable = ResolvedCallable(
                        implementation_method,
                        dispatch_class_key=implementation.key,
                    )
                    candidates[(implementation_method.key, implementation.key)] = candidate
            if len(candidates) == 1:
                return next(iter(candidates.values())), None
            return None, _unresolved(call=call, reason="protocol dispatch")
        target: FunctionDefinition | None = _method_definition(
            class_definition=receiver_class,
            method_name=callee.name,
            index=index,
            cache=method_cache,
            active=frozenset(),
        )
        if target is not None:
            return ResolvedCallable(target, dispatch_class_key=receiver_class.key), None
        reason: str = "self method" if _is_direct_self_receiver(receiver) else "dynamic attribute"
        return None, _unresolved(call=call, reason=reason)
    root_name: str | None = _root_name(receiver)
    if root_name in untyped_parameters:
        return None, _unresolved(call=call, reason="parameter method")
    if _is_direct_self_receiver(receiver):
        return None, _unresolved(call=call, reason="self method")
    if project_owned:
        return None, _unresolved(call=call, reason="dynamic attribute")
    if root_name is not None and root_name in local_types:
        return None, None
    key = _imported_module_call_key(call=callee, definition=definition)
    target = index.get_function(key) if key is not None else None
    return ResolvedCallable(target) if target is not None else None, None


def _receiver_class(
    *,
    expression: MappingExpression,
    definition: FunctionDefinition,
    dispatch_class_key: str | None,
    index: SymbolResolver,
    local_types: dict[str, str | None],
    method_cache: dict[tuple[str, str, bool], FunctionDefinition | None],
) -> tuple[ClassDefinition | None, bool]:
    if expression.kind == MAPPING_EXPRESSION_NAME:
        if expression.name in METHOD_RECEIVER_NAMES and definition.owning_class is not None:
            class_key: str = dispatch_class_key or ClassDefinition.build_key(
                module_name=definition.module_name,
                name=definition.owning_class,
            )
            return index.get_class(class_key), True
        if expression.name in local_types:
            local_key: str | None = local_types[expression.name]
            return (index.get_class(local_key), True) if local_key is not None else (None, False)
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
    if expression.kind == MAPPING_EXPRESSION_CALL and expression.child is not None:
        constructor: ClassDefinition | None = None
        constructor_root: str | None = _root_name(expression.child)
        if constructor_root is None or constructor_root not in local_types:
            constructor = _resolve_class_expression(
                expression=expression.child, definition=definition, index=index
            )
        if constructor is not None:
            return constructor, True
        factory: FunctionDefinition | None = _called_function(
            call=MappingCall(callee=expression.child, line=0),
            definition=definition,
            dispatch_class_key=dispatch_class_key,
            index=index,
            local_types=local_types,
            method_cache=method_cache,
        )
        if factory is None or factory.syntax.returns is None:
            return None, factory is not None
        returned: ClassDefinition | None = _resolve_class_expression(
            expression=factory.syntax.returns,
            definition=factory,
            index=index,
            annotation=True,
        )
        return returned, returned is not None
    if expression.kind == MAPPING_EXPRESSION_ATTRIBUTE and expression.child is not None:
        owner, project_owned = _receiver_class(
            expression=expression.child,
            definition=definition,
            dispatch_class_key=dispatch_class_key,
            index=index,
            local_types=local_types,
            method_cache=method_cache,
        )
        if owner is None:
            return None, project_owned
        reference: ClassReference | None = owner.instance_attributes.get(expression.name)
        if reference is None:
            reference = owner.class_attributes.get(expression.name)
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
    call: MappingCall,
    definition: FunctionDefinition,
    dispatch_class_key: str | None,
    index: SymbolResolver,
    local_types: dict[str, str | None],
    method_cache: dict[tuple[str, str, bool], FunctionDefinition | None],
) -> FunctionDefinition | None:
    callee: MappingExpression = call.callee
    if callee.kind == MAPPING_EXPRESSION_NAME:
        if callee.name in local_types:
            return None
        key: str | None = _top_level_call_key(call=callee, definition=definition)
        return index.get_function(key) if key is not None else None
    if callee.kind != MAPPING_EXPRESSION_ATTRIBUTE or callee.child is None:
        return None
    receiver, _ = _receiver_class(
        expression=callee.child,
        definition=definition,
        dispatch_class_key=dispatch_class_key,
        index=index,
        local_types=local_types,
        method_cache=method_cache,
    )
    if receiver is not None:
        return _method_definition(
            class_definition=receiver,
            method_name=callee.name,
            index=index,
            cache=method_cache,
            active=frozenset(),
        )
    root_name: str | None = _root_name(callee.child)
    if root_name is not None and root_name in local_types:
        return None
    key = _imported_module_call_key(call=callee, definition=definition)
    return index.get_function(key) if key is not None else None


def _method_definition(
    *,
    class_definition: ClassDefinition,
    method_name: str,
    index: SymbolResolver,
    cache: dict[tuple[str, str, bool], FunctionDefinition | None],
    active: frozenset[tuple[str, str]],
    exclude_protocol_bases: bool = False,
) -> FunctionDefinition | None:
    cache_key: tuple[str, str, bool] = (
        class_definition.key,
        method_name,
        exclude_protocol_bases,
    )
    active_key: tuple[str, str] = (class_definition.key, method_name)
    if cache_key in cache:
        return cache[cache_key]
    if active_key in active:
        return None
    direct_key: str = FunctionDefinition.build_key(
        module_name=class_definition.module_name,
        name=method_name,
        owning_class=class_definition.name,
    )
    direct: FunctionDefinition | None = index.get_function(direct_key)
    if direct is not None:
        cache[cache_key] = direct
        return direct
    candidates: dict[str, FunctionDefinition] = {}
    next_active: frozenset[tuple[str, str]] = active | {active_key}
    for base in class_definition.bases:
        base_class: ClassDefinition | None = _resolve_class_expression(
            expression=base,
            definition=class_definition,
            index=index,
        )
        if base_class is None:
            continue
        if exclude_protocol_bases and base_class.protocol:
            continue
        inherited: FunctionDefinition | None = _method_definition(
            class_definition=base_class,
            method_name=method_name,
            index=index,
            cache=cache,
            active=next_active,
            exclude_protocol_bases=exclude_protocol_bases,
        )
        if inherited is not None:
            candidates[inherited.key] = inherited
    if len(candidates) == 1:
        result: FunctionDefinition | None = next(iter(candidates.values()))
    else:
        result = None
    cache[cache_key] = result
    return result


def _resolve_class_expression(
    *,
    expression: MappingExpression,
    definition: FunctionDefinition | ClassDefinition,
    index: SymbolResolver,
    annotation: bool = False,
) -> ClassDefinition | None:
    if expression.kind == MAPPING_EXPRESSION_SUBSCRIPT and expression.child is not None:
        return _resolve_class_expression(
            expression=expression.child,
            definition=definition,
            index=index,
            annotation=annotation,
        )
    if expression.kind == MAPPING_EXPRESSION_STRING and expression.string_value is not None:
        parsed: MappingExpression | None = _forward_expression(expression.string_value)
        if parsed is None:
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
    if expression.kind == MAPPING_EXPRESSION_NAME:
        local: ClassDefinition | None = index.get_class(
            ClassDefinition.build_key(module_name=definition.module_name, name=expression.name)
        )
        if local is not None:
            return local
        imported: tuple[str, str] | None = imports.symbols.get(expression.name)
        if imported is not None:
            imported_key: str = ClassDefinition.build_key(module_name=imported[0], name=imported[1])
            return index.get_class(imported_key)
        return None
    if expression.kind == MAPPING_EXPRESSION_ATTRIBUTE:
        spelling: str = _expression_name(expression)
        first, separator, remainder = spelling.partition(".")
        imported_module: str | None = imports.modules.get(first)
        if separator and imported_module is not None:
            spelling = f"{imported_module}.{remainder}"
        return index.get_class(spelling)
    return None


def _receiver_states(
    *,
    definition: FunctionDefinition,
    dispatch_class_key: str | None,
    index: SymbolResolver,
    method_cache: dict[tuple[str, str, bool], FunctionDefinition | None],
) -> dict[MappingCall, dict[str, str | None]]:
    bindings: dict[str, str | None] = {name: None for name in _parameter_names(definition)}
    invalid: set[str] = set()
    for argument in definition.syntax.parameters:
        if argument.annotation is None:
            continue
        class_definition: ClassDefinition | None = _resolve_class_expression(
            expression=argument.annotation,
            definition=definition,
            index=index,
            annotation=True,
        )
        if class_definition is not None:
            bindings[argument.name] = class_definition.key
    states: dict[MappingCall, dict[str, str | None]] = {
        call: dict(bindings) for call in definition.syntax.calls
    }
    for statement in definition.syntax.statements:
        statement_calls: tuple[MappingCall, ...] = statement.calls
        if statement.control_flow:
            assigned_names: frozenset[str] = statement.assigned_names
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
            assigned_names = statement.assigned_names
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
    statement: MappingStatement,
    definition: FunctionDefinition,
    dispatch_class_key: str | None,
    index: SymbolResolver,
    bindings: dict[str, str | None],
    method_cache: dict[tuple[str, str, bool], FunctionDefinition | None],
) -> tuple[str | None, ClassDefinition | None]:
    if statement.binding_name is not None and statement.binding_annotation is not None:
        return statement.binding_name, _resolve_class_expression(
            expression=statement.binding_annotation,
            definition=definition,
            index=index,
            annotation=True,
        )
    if statement.binding_name is not None and statement.binding_value is not None:
        target: str = statement.binding_name
        value: MappingExpression = statement.binding_value
        if value.kind == MAPPING_EXPRESSION_CALL and value.child is not None:
            constructor: ClassDefinition | None = None
            constructor_root: str | None = _root_name(value.child)
            if constructor_root is None or constructor_root not in bindings:
                constructor = _resolve_class_expression(
                    expression=value.child,
                    definition=definition,
                    index=index,
                )
            if constructor is not None:
                return target, constructor
            factory: FunctionDefinition | None = _called_function(
                call=MappingCall(callee=value.child, line=0),
                definition=definition,
                dispatch_class_key=dispatch_class_key,
                index=index,
                local_types=bindings,
                method_cache=method_cache,
            )
            if factory is None or factory.syntax.returns is None:
                return target, None
            return target, _resolve_class_expression(
                expression=factory.syntax.returns,
                definition=factory,
                index=index,
                annotation=True,
            )
        if value.kind == MAPPING_EXPRESSION_NAME:
            alias_key: str | None = bindings.get(value.name)
            return target, index.get_class(alias_key) if alias_key is not None else None
        return target, None
    if statement.binding_name is not None:
        return statement.binding_name, None
    return None, None


def _dispatch_class_name(
    *, definition: FunctionDefinition, dispatch_class_key: str | None, index: SymbolResolver
) -> str | None:
    if definition.owning_class is None or dispatch_class_key is None:
        return None
    dispatch_class: ClassDefinition | None = index.get_class(dispatch_class_key)
    if dispatch_class is None or dispatch_class.name == definition.owning_class:
        return None
    return dispatch_class.name


def _top_level_call_key(*, call: MappingExpression, definition: FunctionDefinition) -> str:
    imported: tuple[str, str] | None = definition.imports.runtime.symbols.get(call.name)
    if imported is not None:
        return FunctionDefinition.build_key(module_name=imported[0], name=imported[1])
    return FunctionDefinition.build_key(module_name=definition.module_name, name=call.name)


def _imported_module_call_key(
    *, call: MappingExpression, definition: FunctionDefinition
) -> str | None:
    if call.child is None or call.child.kind != MAPPING_EXPRESSION_NAME:
        return None
    imported_module: str | None = definition.imports.runtime.modules.get(call.child.name)
    if imported_module is None:
        return None
    return FunctionDefinition.build_key(module_name=imported_module, name=call.name)


def _unresolved(*, call: MappingCall, reason: str) -> UnresolvedCall:
    return UnresolvedCall(name=call.callee.spelling, line=call.line, reason=reason)


def _is_direct_self_receiver(expression: MappingExpression) -> bool:
    return expression.kind == MAPPING_EXPRESSION_NAME and expression.name in METHOD_RECEIVER_NAMES


def _expression_name(node: MappingExpression) -> str:
    return ".".join(node.parts)


def _root_name(node: MappingExpression) -> str | None:
    while node.kind == MAPPING_EXPRESSION_ATTRIBUTE and node.child is not None:
        node = node.child
    return node.name if node.kind == MAPPING_EXPRESSION_NAME else None


def _parameter_names(definition: FunctionDefinition) -> frozenset[str]:
    return frozenset(parameter.name for parameter in definition.syntax.parameters)


def _untyped_parameter_names(
    definition: FunctionDefinition,
) -> frozenset[str]:
    names: set[str] = {
        parameter.name for parameter in definition.syntax.parameters if parameter.annotation is None
    }
    names.discard(SELF_RECEIVER_NAME)
    names.discard(CLASS_RECEIVER_NAME)
    return frozenset(names)


def _forward_expression(value: str) -> MappingExpression | None:
    spelling: str = "".join(value.split())
    base: str = spelling.split("[", maxsplit=1)[0]
    parts: tuple[str, ...] = tuple(base.split("."))
    if not parts or any(not part.isidentifier() for part in parts):
        return None
    expression: MappingExpression = MappingExpression(
        MAPPING_EXPRESSION_NAME, parts[0], (parts[0],)
    )
    for part in parts[1:]:
        expression = MappingExpression(
            MAPPING_EXPRESSION_ATTRIBUTE,
            f"{expression.spelling}.{part}",
            (*expression.parts, part),
            child=expression,
        )
    if SUBSCRIPT_OPEN in spelling:
        expression = MappingExpression(
            MAPPING_EXPRESSION_SUBSCRIPT, spelling, expression.parts, child=expression
        )
    return expression
