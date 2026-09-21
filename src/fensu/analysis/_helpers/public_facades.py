"""Deterministic recognition of root-level public API facades."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from enum import StrEnum

_ALL_NAME: str = "__all__"
_CONTEXTLIB_MODULE: str = "contextlib"
_CONTEXT_MANAGER_NAMES: tuple[str, ...] = ("asynccontextmanager", "contextmanager")
_FUTURE_MODULE: str = "__future__"
_IGNORED_ASSIGNMENT_NAME: str = "_"
_OVERLOAD_NAME: str = "overload"
_TYPING_MODULE: str = "typing"


class _ImportedKind(StrEnum):
    CONTEXT_MANAGER = "contextmanager"
    OTHER = "other"
    OVERLOAD = "overload"


@dataclass(frozen=True, slots=True)
class _Binding:
    internal: bool
    kind: _ImportedKind = _ImportedKind.OTHER


def is_public_facade(*, module: ast.Module, package_name: str) -> bool:
    """Return whether a module is a statically bounded public API facade."""

    exports: frozenset[str] | None = _static_exports(module)
    if not exports:
        return False
    imports: dict[str, _Binding] = _imported_bindings(module=module, package_name=package_name)
    local_declarations: frozenset[str] = frozenset(
        statement.name
        for statement in module.body
        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    )
    supported: set[str] = {name for name, binding in imports.items() if binding.internal}
    for statement in module.body:
        if _is_docstring(statement) or isinstance(statement, (ast.Import, ast.ImportFrom)):
            continue
        if _is_all_assignment(statement):
            if isinstance(statement, ast.AnnAssign) and _contains_call(statement.annotation):
                return False
            continue
        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if statement.name not in exports:
                return False
            if _function_has_import_time_behavior(function=statement):
                return False
            body: list[ast.stmt] = _without_docstring(statement.body)
            if _overload_stub(function=statement, body=body, imports=imports):
                continue
            internal: bool | None = _facade_function(
                function=statement,
                imports=imports,
                local_declarations=local_declarations,
            )
            if not internal:
                return False
            supported.add(statement.name)
            continue
        if isinstance(statement, ast.ClassDef):
            if statement.name not in exports:
                return False
            internal = _facade_class(class_node=statement, imports=imports)
            if not internal:
                return False
            supported.add(statement.name)
            continue
        if isinstance(statement, ast.AnnAssign) and _contains_call(statement.annotation):
            return False
        alias: tuple[str, str] | None = _import_alias(statement)
        if (
            alias is None
            or alias[0] not in exports
            or alias[1] not in imports
            or not imports[alias[1]].internal
        ):
            return False
        supported.add(alias[0])
    return exports <= supported


def _static_exports(module: ast.Module) -> frozenset[str] | None:
    assignments: list[ast.stmt] = [
        statement for statement in module.body if _is_all_assignment(statement)
    ]
    if len(assignments) != 1:
        return None
    statement: ast.stmt = assignments[0]
    value: ast.expr | None = (
        statement.value if isinstance(statement, (ast.Assign, ast.AnnAssign)) else None
    )
    if not isinstance(value, (ast.List, ast.Tuple)) or not value.elts:
        return None
    names: list[str] = []
    for item in value.elts:
        if not isinstance(item, ast.Constant) or not isinstance(item.value, str):
            return None
        names.append(item.value)
    if len(names) != len(set(names)):
        return None
    return frozenset(names)


def _imported_bindings(*, module: ast.Module, package_name: str) -> dict[str, _Binding]:
    bindings: dict[str, _Binding] = {}
    for statement in module.body:
        if isinstance(statement, ast.Import):
            for alias in statement.names:
                name: str = alias.asname or alias.name.partition(".")[0]
                internal: bool = alias.name == package_name or alias.name.startswith(
                    f"{package_name}."
                )
                bindings[name] = _Binding(internal=internal)
        elif isinstance(statement, ast.ImportFrom) and statement.module != _FUTURE_MODULE:
            internal = (
                statement.level > 0
                or statement.module == package_name
                or bool(statement.module and statement.module.startswith(f"{package_name}."))
            )
            for alias in statement.names:
                kind: _ImportedKind = _ImportedKind.OTHER
                if statement.module == _CONTEXTLIB_MODULE and alias.name in _CONTEXT_MANAGER_NAMES:
                    kind = _ImportedKind.CONTEXT_MANAGER
                elif statement.module == _TYPING_MODULE and alias.name == _OVERLOAD_NAME:
                    kind = _ImportedKind.OVERLOAD
                bindings[alias.asname or alias.name] = _Binding(internal=internal, kind=kind)
    return bindings


def _facade_function(
    *,
    function: ast.FunctionDef | ast.AsyncFunctionDef,
    imports: dict[str, _Binding],
    local_declarations: frozenset[str],
) -> bool | None:
    if _function_has_import_time_behavior(function=function):
        return None
    body: list[ast.stmt] = _without_docstring(function.body)
    if _context_manager_wrapper(
        function=function,
        body=body,
        imports=imports,
        local_declarations=local_declarations,
    ):
        statement: ast.stmt = body[0]
        if not isinstance(statement, (ast.With, ast.AsyncWith)):
            return None
        binding: _Binding | None = _imported_call_binding(
            expression=statement.items[0].context_expr, imports=imports
        )
        return None if binding is None else binding.internal
    if function.decorator_list or len(body) != 1:
        return None
    statement: ast.stmt = body[0]
    expression: ast.expr | None = None
    if isinstance(statement, (ast.Return, ast.Expr)):
        expression = statement.value
    elif (
        isinstance(statement, ast.Assign)
        and len(statement.targets) == 1
        and isinstance(statement.targets[0], ast.Name)
        and statement.targets[0].id == _IGNORED_ASSIGNMENT_NAME
    ):
        expression = statement.value
    if _function_shadows_call(
        function=function,
        expression=expression,
        local_declarations=local_declarations,
    ):
        return None
    binding = _imported_call_binding(expression=expression, imports=imports)
    return None if binding is None else binding.internal


def _function_has_import_time_behavior(*, function: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    parameters: list[ast.arg] = [
        *function.args.posonlyargs,
        *function.args.args,
        *function.args.kwonlyargs,
        *((function.args.vararg,) if function.args.vararg is not None else ()),
        *((function.args.kwarg,) if function.args.kwarg is not None else ()),
    ]
    annotations: list[ast.expr] = [
        *(parameter.annotation for parameter in parameters if parameter.annotation is not None),
        *((function.returns,) if function.returns is not None else ()),
    ]
    defaults: list[ast.expr] = [
        *function.args.defaults,
        *(value for value in function.args.kw_defaults if value is not None),
    ]
    return any(_contains_call(value) for value in annotations) or any(
        _contains_call(value) or isinstance(value, (ast.Dict, ast.List, ast.Set))
        for value in defaults
    )


def _overload_stub(
    *,
    function: ast.FunctionDef | ast.AsyncFunctionDef,
    body: list[ast.stmt],
    imports: dict[str, _Binding],
) -> bool:
    return (
        len(function.decorator_list) == 1
        and _decorator_kind(function=function, imports=imports) is _ImportedKind.OVERLOAD
        and len(body) == 1
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and body[0].value.value is Ellipsis
    )


def _context_manager_wrapper(
    *,
    function: ast.FunctionDef | ast.AsyncFunctionDef,
    body: list[ast.stmt],
    imports: dict[str, _Binding],
    local_declarations: frozenset[str],
) -> bool:
    if (
        len(function.decorator_list) != 1
        or _decorator_kind(function=function, imports=imports) is not _ImportedKind.CONTEXT_MANAGER
        or len(body) != 1
        or not isinstance(body[0], (ast.With, ast.AsyncWith))
        or len(body[0].items) != 1
        or _imported_call_binding(expression=body[0].items[0].context_expr, imports=imports) is None
        or _function_shadows_call(
            function=function,
            expression=body[0].items[0].context_expr,
            local_declarations=local_declarations,
        )
        or len(body[0].body) != 1
        or not isinstance(body[0].body[0], ast.Expr)
    ):
        return False
    yielded: ast.expr = body[0].body[0].value
    if not isinstance(yielded, ast.Yield):
        return False
    optional_vars: ast.expr | None = body[0].items[0].optional_vars
    if optional_vars is None:
        return yielded.value is None
    return (
        isinstance(optional_vars, ast.Name)
        and isinstance(yielded.value, ast.Name)
        and optional_vars.id == yielded.value.id
    )


def _function_shadows_call(
    *,
    function: ast.FunctionDef | ast.AsyncFunctionDef,
    expression: ast.expr | None,
    local_declarations: frozenset[str],
) -> bool:
    root: str | None = _call_root(expression)
    if root is None:
        return False
    parameters: tuple[ast.arg, ...] = (
        *function.args.posonlyargs,
        *function.args.args,
        *function.args.kwonlyargs,
        *((function.args.vararg,) if function.args.vararg is not None else ()),
        *((function.args.kwarg,) if function.args.kwarg is not None else ()),
    )
    return root in local_declarations or any(parameter.arg == root for parameter in parameters)


def _call_root(expression: ast.expr | None) -> str | None:
    if isinstance(expression, ast.Await):
        expression = expression.value
    if not isinstance(expression, ast.Call):
        return None
    target: ast.expr = expression.func
    while isinstance(target, ast.Attribute):
        target = target.value
    return target.id if isinstance(target, ast.Name) else None


def _decorator_kind(
    *, function: ast.FunctionDef | ast.AsyncFunctionDef, imports: dict[str, _Binding]
) -> _ImportedKind | None:
    decorator: ast.expr = function.decorator_list[0]
    binding: _Binding | None = (
        imports.get(decorator.id) if isinstance(decorator, ast.Name) else None
    )
    return None if binding is None else binding.kind


def _facade_class(*, class_node: ast.ClassDef, imports: dict[str, _Binding]) -> bool | None:
    if class_node.decorator_list or len(class_node.bases) != 1 or class_node.keywords:
        return None
    if any(
        not isinstance(statement, ast.Pass) for statement in _without_docstring(class_node.body)
    ):
        return None
    binding: _Binding | None = _imported_expression_binding(
        expression=class_node.bases[0], imports=imports
    )
    return None if binding is None else binding.internal


def _imported_call_binding(
    *, expression: ast.expr | None, imports: dict[str, _Binding]
) -> _Binding | None:
    if isinstance(expression, ast.Await):
        expression = expression.value
    if not isinstance(expression, ast.Call):
        return None
    values: list[ast.expr] = [*expression.args, *(keyword.value for keyword in expression.keywords)]
    if any(not _forwarded_value(value) for value in values):
        return None
    return _imported_expression_binding(expression=expression.func, imports=imports)


def _imported_expression_binding(
    *, expression: ast.expr, imports: dict[str, _Binding]
) -> _Binding | None:
    while isinstance(expression, ast.Attribute):
        expression = expression.value
    return imports.get(expression.id) if isinstance(expression, ast.Name) else None


def _forwarded_value(expression: ast.expr) -> bool:
    if isinstance(expression, (ast.Name, ast.Constant)):
        return True
    if isinstance(expression, ast.Attribute):
        return _forwarded_value(expression.value)
    if isinstance(expression, ast.Starred):
        return _forwarded_value(expression.value)
    if isinstance(expression, (ast.List, ast.Tuple)):
        return all(_forwarded_value(item) for item in expression.elts)
    return False


def _contains_call(node: ast.AST) -> bool:
    return isinstance(node, ast.Call) or any(
        _contains_call(child) for child in ast.iter_child_nodes(node)
    )


def _import_alias(statement: ast.stmt) -> tuple[str, str] | None:
    if (
        isinstance(statement, ast.Assign)
        and len(statement.targets) == 1
        and isinstance(statement.targets[0], ast.Name)
        and isinstance(statement.value, ast.Name)
    ):
        return statement.targets[0].id, statement.value.id
    if (
        isinstance(statement, ast.AnnAssign)
        and isinstance(statement.target, ast.Name)
        and isinstance(statement.value, ast.Name)
    ):
        return statement.target.id, statement.value.id
    return None


def _is_all_assignment(statement: ast.stmt) -> bool:
    if isinstance(statement, ast.Assign):
        return any(
            isinstance(target, ast.Name) and target.id == _ALL_NAME for target in statement.targets
        )
    return (
        isinstance(statement, ast.AnnAssign)
        and isinstance(statement.target, ast.Name)
        and statement.target.id == _ALL_NAME
    )


def _is_docstring(statement: ast.stmt) -> bool:
    return (
        isinstance(statement, ast.Expr)
        and isinstance(statement.value, ast.Constant)
        and isinstance(statement.value.value, str)
    )


def _without_docstring(body: list[ast.stmt]) -> list[ast.stmt]:
    return body[1:] if body and _is_docstring(body[0]) else body
