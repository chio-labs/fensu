"""AST classification helpers for role ownership rules."""

from __future__ import annotations

import ast

from strata.rules.roles.types import RoleSymbol

_type_class_base_names: frozenset[str] = frozenset(
    {"Enum", "IntEnum", "StrEnum", "Flag", "IntFlag", "NamedTuple", "Protocol", "TypedDict"}
)
_model_class_base_names: frozenset[str] = frozenset({"BaseModel"})


def is_type_class(node: ast.ClassDef) -> bool:
    """Return whether a class is owned by the type layer."""

    if is_dataclass_class(node) or inherits_from_base_names(
        node=node, base_names=_model_class_base_names
    ):
        return False
    return inherits_from_base_names(node=node, base_names=_type_class_base_names)


def is_model_class(node: ast.ClassDef) -> bool:
    """Return whether a public class is a structured runtime model."""

    if node.name.startswith("_"):
        return False
    return is_dataclass_class(node) or inherits_from_base_names(
        node=node, base_names=_model_class_base_names
    )


def is_exception_class(node: ast.ClassDef) -> bool:
    """Return whether a class declaration looks like a custom exception."""

    if node.name.endswith(("Error", "Exception")):
        return True
    return any((base_name(base) or "").endswith(("Error", "Exception")) for base in node.bases)


def is_dataclass_class(node: ast.ClassDef) -> bool:
    """Return whether a class has a dataclass decorator."""

    return any(decorator_name(decorator).endswith("dataclass") for decorator in node.decorator_list)


def is_type_checking_import_block(node: ast.stmt) -> bool:
    """Return whether a statement is an import-only TYPE_CHECKING block."""

    if not isinstance(node, ast.If) or node.orelse:
        return False
    test_name: str | None = None
    if isinstance(node.test, ast.Name):
        test_name = node.test.id
    elif isinstance(node.test, ast.Attribute):
        test_name = node.test.attr
    return test_name == RoleSymbol.TYPE_CHECKING_SYMBOL and all(
        isinstance(statement, ast.Import | ast.ImportFrom) for statement in node.body
    )


def is_newtype_assignment(node: ast.stmt) -> bool:
    """Return whether a statement assigns the result of NewType."""

    value: ast.expr | None = None
    if isinstance(node, ast.Assign):
        value = node.value
    elif isinstance(node, ast.AnnAssign):
        value = node.value
    return (
        isinstance(value, ast.Call)
        and isinstance(value.func, ast.Name | ast.Attribute)
        and base_name(value.func) == RoleSymbol.NEW_TYPE
    )


def is_public_type_alias(node: ast.stmt) -> bool:
    """Return whether a statement defines a public explicit type alias."""

    if (
        isinstance(node, ast.TypeAlias)
        and isinstance(node.name, ast.Name)
        and not node.name.id.startswith("_")
    ):
        return True
    return (
        isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and not node.target.id.startswith("_")
        and base_name(node.annotation) == RoleSymbol.TYPE_ALIAS
    )


def non_docstring_body(module: ast.Module) -> tuple[ast.stmt, ...]:
    """Return module statements without a leading docstring."""

    if not module.body:
        return ()
    first: ast.stmt = module.body[0]
    if (
        isinstance(first, ast.Expr)
        and isinstance(first.value, ast.Constant)
        and isinstance(first.value.value, str)
    ):
        return tuple(module.body[1:])
    return tuple(module.body)


def decorator_name(node: ast.expr) -> str:
    """Return a decorator's dotted name when statically knowable."""

    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent: str = decorator_name(node.value)
        return node.attr if not parent else f"{parent}.{node.attr}"
    if isinstance(node, ast.Call):
        return decorator_name(node.func)
    return ""


def inherits_from_base_names(*, node: ast.ClassDef, base_names: frozenset[str]) -> bool:
    """Return whether a class directly inherits from a named base."""

    return any(base_name(base) in base_names for base in node.bases)


def base_name(node: ast.expr) -> str | None:
    """Return the rightmost name of an expression."""

    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Subscript):
        return base_name(node.value)
    return None
