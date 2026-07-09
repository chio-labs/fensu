"""Rule check functions for the roles family."""

from __future__ import annotations

import ast

from strata.rules.authoring.models import Fault
from strata.rules.authoring.types import RuleContext
from strata.rules.roles.helpers.classification import (
    is_exception_class,
    is_model_class,
    is_newtype_assignment,
    is_public_type_alias,
    is_type_checking_import_block,
    is_type_class,
    non_docstring_body,
)

_banned_generic_filenames: frozenset[str] = frozenset(
    {"base.py", "common.py", "helpers.py", "misc.py"}
)


def models_only_models(module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag foreign declarations in model-role modules."""

    if ctx.role_of() != "models":
        return []
    faults: list[Fault] = []
    for node in non_docstring_body(module):
        if isinstance(node, ast.Import | ast.ImportFrom):
            continue
        if isinstance(node, ast.ClassDef) and is_model_class(node):
            continue
        faults.append(ctx.fault(node))
    return faults


def types_only_types(module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag runtime declarations in type-role modules."""

    if ctx.role_of() != "types":
        return []
    faults: list[Fault] = []
    allowed_nodes: tuple[type[ast.stmt], ...] = (
        ast.Import,
        ast.ImportFrom,
        ast.Assign,
        ast.AnnAssign,
        ast.TypeAlias,
    )
    for node in non_docstring_body(module):
        if isinstance(node, allowed_nodes) or is_type_checking_import_block(node):
            continue
        if isinstance(node, ast.ClassDef) and is_type_class(node):
            continue
        faults.append(ctx.fault(node))
    return faults


def constants_only_constants(module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag foreign declarations in constant-role modules."""

    if ctx.role_of() != "constants":
        return []
    allowed_nodes: tuple[type[ast.stmt], ...] = (
        ast.Import,
        ast.ImportFrom,
        ast.Assign,
        ast.AnnAssign,
    )
    return [
        ctx.fault(node)
        for node in non_docstring_body(module)
        if not isinstance(node, allowed_nodes)
    ]


def exceptions_only_exceptions(module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag foreign declarations in exception-role modules."""

    if ctx.role_of() != "exceptions":
        return []
    faults: list[Fault] = []
    for node in non_docstring_body(module):
        if isinstance(node, ast.Import | ast.ImportFrom):
            continue
        if isinstance(node, ast.ClassDef) and is_exception_class(node):
            continue
        faults.append(ctx.fault(node))
    return faults


def model_declaration_outside_models(module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag structured model declarations outside the models role."""

    if ctx.role_of() == "models":
        return []
    return [
        ctx.fault(node)
        for node in ast.walk(module)
        if isinstance(node, ast.ClassDef) and is_model_class(node)
    ]


def type_declaration_outside_types(module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag public type-layer declarations outside the types role."""

    if ctx.role_of() == "types":
        return []
    faults: list[Fault] = []
    for node in ast.walk(module):
        if isinstance(node, ast.ClassDef) and is_type_class(node):
            if node.name.startswith("_") and ctx.in_role("helpers"):
                continue
            faults.append(ctx.fault(node))
        elif isinstance(node, ast.stmt) and (
            is_public_type_alias(node) or is_newtype_assignment(node)
        ):
            faults.append(ctx.fault(node))
    return faults


def constant_outside_constants(module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag public uppercase module constants outside the constants role."""

    if ctx.role_of() == "constants":
        return []
    faults: list[Fault] = []
    for node in non_docstring_body(module):
        for target_name in _assignment_target_names(node):
            if not target_name.startswith("_") and target_name.isupper():
                faults.append(ctx.fault(node))
    return faults


def exception_declaration_outside_exceptions(module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag custom exception declarations outside the exceptions role."""

    if ctx.role_of() == "exceptions":
        return []
    return [
        ctx.fault(node)
        for node in ast.walk(module)
        if isinstance(node, ast.ClassDef) and is_exception_class(node)
    ]


def banned_generic_filename(module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag vague generic module filenames."""

    del module
    if ctx.path.name not in _banned_generic_filenames:
        return []
    return [Fault(code="SFR201", path=ctx.path, message="use a domain-specific filename")]


def helpers_module_name(module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag helpers.py in favor of a helpers package."""

    del module
    if ctx.path.name != "helpers.py":
        return []
    return [Fault(code="SFR202", path=ctx.path, message="use a helpers/ package")]


def classes_module_name(module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag classes.py in favor of a classes package."""

    del module
    if ctx.path.name != "classes.py":
        return []
    return [Fault(code="SFR203", path=ctx.path, message="use a classes/ package")]


def helpers_classes_file_private(module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Flag public plain classes in helpers modules."""

    if not ctx.in_role("helpers"):
        return []
    faults: list[Fault] = []
    for node in module.body:
        if not isinstance(node, ast.ClassDef) or node.name.startswith("_"):
            continue
        if is_model_class(node) or is_type_class(node):
            continue
        faults.append(ctx.fault(node))
    return faults


def _assignment_target_names(node: ast.stmt) -> tuple[str, ...]:
    if isinstance(node, ast.Assign):
        return tuple(target.id for target in node.targets if isinstance(target, ast.Name))
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return (node.target.id,)
    return ()
