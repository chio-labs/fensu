"""Module statement and declaration fact extraction."""

from __future__ import annotations

import ast
from collections.abc import Mapping
from pathlib import Path

from strata.analysis._helpers.locations import source_location
from strata.analysis.models import (
    ModuleDeclarationFacts,
    ModuleStatementFact,
    NamedCallFact,
    SourceLocation,
    TypeDeclarationFact,
)

_model_base_names: frozenset[str] = frozenset({"BaseModel"})
_type_base_names: frozenset[str] = frozenset(
    {"Enum", "IntEnum", "StrEnum", "Flag", "IntFlag", "NamedTuple", "Protocol", "TypedDict"}
)
_type_checking_name: str = "TYPE_CHECKING"
_type_alias_name: str = "TypeAlias"
_new_type_name: str = "NewType"
_future_module_name: str = "__future__"
_all_export_name: str = "__all__"
_rule_decorator_name: str = "rule"
_main_role_name: str = "main"
_module_name_variable: str = "__name__"
_main_module_name: str = "__main__"


def module_declaration_facts(
    *,
    path: Path,
    module: ast.Module,
    node_index: Mapping[type[ast.AST], tuple[ast.AST, ...]],
) -> ModuleDeclarationFacts:
    """Return module statement shape and classified declarations."""

    class_kinds: dict[ast.AST, tuple[bool, bool, bool]] = {}
    model_locations: list[SourceLocation] = []
    type_declarations: list[TypeDeclarationFact] = []
    exception_locations: list[SourceLocation] = []
    for node in node_index.get(ast.ClassDef, ()):
        if not isinstance(node, ast.ClassDef):
            continue
        model_class: bool = _is_model_class(node)
        type_class: bool = _is_type_class(node)
        exception_class: bool = _is_exception_class(node)
        class_kinds[node] = (model_class, type_class, exception_class)
        location: SourceLocation = source_location(path=path, node=node)
        if model_class:
            model_locations.append(location)
        if type_class:
            type_declarations.append(
                TypeDeclarationFact(location=location, private=node.name.startswith("_"))
            )
        if exception_class:
            exception_locations.append(location)
    body: list[ast.stmt] = module.body
    if body and _is_docstring(body[0]):
        body = body[1:]
    statements: list[ModuleStatementFact] = []
    all_assignment_locations: list[SourceLocation] = []
    for node in body:
        model_class, type_class, exception_class = class_kinds.get(node, (False, False, False))
        all_assignment: bool = _is_all_assignment(node)
        statements.append(
            ModuleStatementFact(
                location=source_location(path=path, node=node),
                import_statement=isinstance(node, ast.Import | ast.ImportFrom),
                assignment_statement=isinstance(node, ast.Assign | ast.AnnAssign),
                explicit_type_alias=isinstance(node, ast.TypeAlias),
                type_checking_import_block=_is_type_checking_import_block(node),
                model_class=model_class,
                type_class=type_class,
                exception_class=exception_class,
                assignment_target_names=_assignment_target_names(node),
                function_name=(
                    node.name if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) else None
                ),
                class_name=node.name if isinstance(node, ast.ClassDef) else None,
                dataclass_class=isinstance(node, ast.ClassDef) and _is_dataclass_class(node),
                docstring_statement=_is_docstring(node),
                all_assignment=all_assignment,
                rule_decorated_function=isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
                and any(
                    _decorator_name(item).split(".")[-1] == _rule_decorator_name
                    for item in node.decorator_list
                ),
                nonexecuting_import_guard=isinstance(node, ast.If)
                and _is_nonexecuting_guard(node.test),
            )
        )
        if all_assignment:
            all_assignment_locations.append(source_location(path=path, node=node))
    for node_type in (ast.Assign, ast.AnnAssign, ast.TypeAlias):
        for node in node_index.get(node_type, ()):
            if isinstance(node, ast.stmt) and (_is_public_type_alias(node) or _is_newtype(node)):
                type_declarations.append(
                    TypeDeclarationFact(
                        location=source_location(path=path, node=node), private=False
                    )
                )
    imported_main_entry_names: set[str] = set()
    for node in module.body:
        if not isinstance(node, ast.ImportFrom) or node.module is None:
            continue
        if _main_role_name in node.module.split("."):
            imported_main_entry_names.update(alias.asname or alias.name for alias in node.names)
    main_function: ast.FunctionDef | ast.AsyncFunctionDef | None = next(
        (
            node
            for node in module.body
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
            and node.name == _main_role_name
        ),
        None,
    )
    main_calls: tuple[NamedCallFact, ...] = ()
    if main_function is not None:
        main_calls = tuple(
            NamedCallFact(
                location=source_location(path=path, node=call),
                name=call.func.id if isinstance(call.func, ast.Name) else None,
            )
            for call in ast.walk(main_function)
            if isinstance(call, ast.Call)
        )
    return ModuleDeclarationFacts(
        statements=tuple(statements),
        empty_or_docstring_only=not module.body
        or (len(module.body) == 1 and _is_docstring(module.body[0])),
        pure_reexport=_is_pure_reexport(module),
        top_level_class_count=len([node for node in module.body if isinstance(node, ast.ClassDef)]),
        all_assignment_locations=tuple(all_assignment_locations),
        import_time_call_locations=tuple(
            source_location(path=path, node=node) for node in _import_time_bare_calls(module)
        ),
        imported_main_entry_names=frozenset(imported_main_entry_names),
        main_calls=main_calls,
        model_locations=tuple(model_locations),
        type_declarations=tuple(type_declarations),
        exception_locations=tuple(exception_locations),
    )


def _is_model_class(node: ast.ClassDef) -> bool:
    if node.name.startswith("_"):
        return False
    return _is_dataclass_class(node) or any(
        _base_name(base) in _model_base_names for base in node.bases
    )


def _is_dataclass_class(node: ast.ClassDef) -> bool:
    return any(_decorator_name(item).endswith("dataclass") for item in node.decorator_list)


def _is_type_class(node: ast.ClassDef) -> bool:
    if _is_dataclass_class(node) or any(
        _base_name(base) in _model_base_names for base in node.bases
    ):
        return False
    return any(_base_name(base) in _type_base_names for base in node.bases)


def _is_exception_class(node: ast.ClassDef) -> bool:
    return node.name.endswith(("Error", "Exception")) or any(
        (_base_name(base) or "").endswith(("Error", "Exception")) for base in node.bases
    )


def _is_type_checking_import_block(node: ast.stmt) -> bool:
    return (
        isinstance(node, ast.If)
        and not node.orelse
        and _base_name(node.test) == _type_checking_name
        and all(isinstance(item, ast.Import | ast.ImportFrom) for item in node.body)
    )


def _is_public_type_alias(node: ast.stmt) -> bool:
    if isinstance(node, ast.TypeAlias) and isinstance(node.name, ast.Name):
        return not node.name.id.startswith("_")
    return (
        isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and not node.target.id.startswith("_")
        and _base_name(node.annotation) == _type_alias_name
    )


def _is_newtype(node: ast.stmt) -> bool:
    value: ast.expr | None = None
    if isinstance(node, ast.Assign):
        value = node.value
    elif isinstance(node, ast.AnnAssign):
        value = node.value
    return (
        isinstance(value, ast.Call)
        and isinstance(value.func, ast.Name | ast.Attribute)
        and _base_name(value.func) == _new_type_name
    )


def _assignment_target_names(node: ast.stmt) -> tuple[str, ...]:
    if isinstance(node, ast.Assign):
        return tuple(target.id for target in node.targets if isinstance(target, ast.Name))
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return (node.target.id,)
    return ()


def _decorator_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent: str = _decorator_name(node.value)
        return node.attr if not parent else f"{parent}.{node.attr}"
    if isinstance(node, ast.Call):
        return _decorator_name(node.func)
    return ""


def _base_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Subscript):
        return _base_name(node.value)
    return None


def _is_docstring(node: ast.stmt) -> bool:
    return (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )


def _is_all_assignment(node: ast.stmt) -> bool:
    return _all_export_name in _assignment_target_names(node)


def _is_pure_reexport(module: ast.Module) -> bool:
    saw_import: bool = False
    saw_all: bool = False
    for node in module.body:
        if _is_docstring(node):
            continue
        if isinstance(node, ast.ImportFrom) and node.module == _future_module_name:
            continue
        if isinstance(node, ast.Import | ast.ImportFrom):
            saw_import = True
            continue
        if _is_all_assignment(node):
            saw_all = True
            continue
        return False
    return saw_import and saw_all


def _import_time_bare_calls(node: ast.AST) -> tuple[ast.Expr, ...]:
    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda):
        return ()
    if isinstance(node, ast.If) and _is_nonexecuting_guard(node.test):
        calls: list[ast.Expr] = []
        for statement in node.orelse:
            calls.extend(_import_time_bare_calls(statement))
        return tuple(calls)
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
        return (node,)
    calls = []
    for child in ast.iter_child_nodes(node):
        calls.extend(_import_time_bare_calls(child))
    return tuple(calls)


def _is_nonexecuting_guard(node: ast.expr) -> bool:
    if isinstance(node, ast.Name) and node.id == _type_checking_name:
        return True
    if not isinstance(node, ast.Compare) or len(node.ops) != 1 or len(node.comparators) != 1:
        return False
    comparator: ast.expr = node.comparators[0]
    return (
        isinstance(node.left, ast.Name)
        and node.left.id == _module_name_variable
        and isinstance(node.ops[0], ast.Eq)
        and isinstance(comparator, ast.Constant)
        and comparator.value == _main_module_name
    )
