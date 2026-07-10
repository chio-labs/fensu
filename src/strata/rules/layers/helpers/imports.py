"""Import-path helpers for layer boundary rules."""

from __future__ import annotations

import ast
from pathlib import Path

from strata.discovery.core.types import RoleName
from strata.rules.authoring.models import Fault
from strata.rules.authoring.types import RuleContext

_source_root_name: str = "src"
_tooling_root_name: str = "scripts"
_init_module_name: str = "__init__"
_minimum_owned_module_parts: int = 3
_minimum_subdomain_module_parts: int = 5
_minimum_internal_import_parts: int = 4
_minimum_public_surface_tail_parts: int = 2
_public_role_names: frozenset[str] = frozenset(
    {RoleName.MODELS, RoleName.TYPES, RoleName.CONSTANTS, RoleName.EXCEPTIONS}
)
_owned_role_names: frozenset[str] = frozenset(
    {
        RoleName.CLASSES,
        RoleName.MAIN,
        RoleName.MODELS,
        RoleName.TYPES,
        RoleName.CONSTANTS,
        RoleName.EXCEPTIONS,
    }
)


def module_parts_for_path(*, path: Path, repo_root: Path) -> tuple[str, ...]:
    """Return importable module parts for a Python file under a src layout."""

    relative_parts: tuple[str, ...] = path.resolve().relative_to(repo_root.resolve()).parts
    if (
        len(relative_parts) >= _minimum_owned_module_parts
        and relative_parts[0] == _source_root_name
    ):
        return (*relative_parts[1:-1], path.stem)
    return (*relative_parts[:-1], path.stem)


def import_from_parts(node: ast.ImportFrom) -> tuple[str, ...]:
    """Return absolute import parts for an ImportFrom node."""

    if node.module is None:
        return ()
    return tuple(node.module.split("."))


def import_alias_parts(alias: ast.alias) -> tuple[str, ...]:
    """Return imported module parts for an Import alias."""

    return tuple(alias.name.split("."))


def is_sibling_internal_import(
    *, current_module_parts: tuple[str, ...], imported_parts: tuple[str, ...]
) -> bool:
    """Return whether an import reaches into a sibling package's internals."""

    if _is_sibling_role_internal_import(
        current_module_parts=current_module_parts, imported_parts=imported_parts
    ):
        return True
    return _is_sibling_subdomain_internal_import(
        current_module_parts=current_module_parts, imported_parts=imported_parts
    )


def _is_sibling_role_internal_import(
    *, current_module_parts: tuple[str, ...], imported_parts: tuple[str, ...]
) -> bool:
    current_package_parts: tuple[str, ...] = current_module_parts[:-1]
    if len(current_package_parts) < _minimum_owned_module_parts:
        return False
    parent_package_parts: tuple[str, ...] = current_package_parts[:-1]
    current_subpackage_name: str = current_package_parts[-1]
    if imported_parts[: len(parent_package_parts)] != parent_package_parts:
        return False
    if len(imported_parts) <= len(parent_package_parts) + 1:
        return False
    sibling_name: str = imported_parts[len(parent_package_parts)]
    if sibling_name == current_subpackage_name:
        return False
    if _is_allowed_sibling_public_surface(
        parent_package_parts=parent_package_parts, imported_parts=imported_parts
    ):
        return False
    return sibling_name not in _allowed_sibling_dependencies(current_subpackage_name)


def _is_sibling_subdomain_internal_import(
    *, current_module_parts: tuple[str, ...], imported_parts: tuple[str, ...]
) -> bool:
    if len(current_module_parts) < _minimum_subdomain_module_parts:
        return False
    current_owner_parts: tuple[str, ...] = current_module_parts[:-2]
    parent_owner_parts: tuple[str, ...] = current_owner_parts[:-1]
    current_owner_name: str = current_owner_parts[-1]
    if imported_parts[: len(parent_owner_parts)] != parent_owner_parts:
        return False
    if len(imported_parts) <= len(parent_owner_parts) + 1:
        return False
    sibling_name: str = imported_parts[len(parent_owner_parts)]
    if sibling_name == current_owner_name:
        return False
    sibling_tail: tuple[str, ...] = imported_parts[len(parent_owner_parts) + 1 :]
    if not sibling_tail:
        return False
    if sibling_tail[0] in _public_role_names:
        return False
    return sibling_tail[0] != RoleName.MAIN


def is_cross_package_internal_import(
    *, current_module_parts: tuple[str, ...], imported_parts: tuple[str, ...]
) -> bool:
    """Return whether an import reaches into another package's internal structure."""

    if (
        len(current_module_parts) < _minimum_owned_module_parts
        or len(imported_parts) < _minimum_owned_module_parts
    ):
        return False
    if imported_parts[0] != current_module_parts[0]:
        return False
    current_domain: str = current_module_parts[1]
    imported_domain: str = imported_parts[1]
    if imported_domain == current_domain:
        return False
    if (
        len(imported_parts) < _minimum_internal_import_parts
        or imported_parts[2] in _public_surface_segments()
    ):
        return False
    return _has_internal_segment(imported_parts[2:])


def import_path_targets_tooling(*, imported_parts: tuple[str, ...]) -> bool:
    """Return whether an absolute import targets the conventional tooling package."""

    return bool(imported_parts) and imported_parts[0] == _tooling_root_name


def private_helper_class_import_faults(
    *, module: ast.Module, ctx: RuleContext, message: str, remediation: str
) -> list[Fault]:
    """Return faults for cross-file references to helper-local private classes."""

    faults: list[Fault] = []
    helper_module_aliases: set[str] = set()
    for node in ast.walk(module):
        if isinstance(node, ast.ImportFrom):
            imported_parts: tuple[str, ...] = import_from_parts(node)
            import_from_faults, import_from_aliases = _helper_import_from_faults(
                node=node,
                imported_parts=imported_parts,
                ctx=ctx,
                message=message,
                remediation=remediation,
            )
            faults.extend(import_from_faults)
            helper_module_aliases.update(import_from_aliases)
        elif isinstance(node, ast.Import):
            import_faults, import_aliases = _helper_import_faults(
                node=node,
                ctx=ctx,
                message=message,
                remediation=remediation,
            )
            faults.extend(import_faults)
            helper_module_aliases.update(import_aliases)
        elif isinstance(node, ast.Attribute) and _is_private_class_name(node.attr):
            if _attribute_base_name(node.value) in helper_module_aliases:
                faults.append(ctx.fault(node, message=message, remediation=remediation))
    return faults


def _helper_import_from_faults(
    *,
    node: ast.ImportFrom,
    imported_parts: tuple[str, ...],
    ctx: RuleContext,
    message: str,
    remediation: str,
) -> tuple[list[Fault], set[str]]:
    faults: list[Fault] = []
    helper_module_aliases: set[str] = set()
    if not _is_helper_module_path(imported_parts):
        return faults, helper_module_aliases
    for alias in node.names:
        imported_name: str = alias.name
        if _is_private_class_name(imported_name):
            faults.append(ctx.fault(node, message=message, remediation=remediation))
            continue
        helper_module_aliases.add(alias.asname or imported_name)
    return faults, helper_module_aliases


def _helper_import_faults(
    *,
    node: ast.Import,
    ctx: RuleContext,
    message: str,
    remediation: str,
) -> tuple[list[Fault], set[str]]:
    faults: list[Fault] = []
    helper_module_aliases: set[str] = set()
    for alias in node.names:
        imported_parts: tuple[str, ...] = import_alias_parts(alias)
        if not _is_helper_module_path(imported_parts):
            continue
        if imported_parts and _is_private_class_name(imported_parts[-1]):
            faults.append(ctx.fault(node, message=message, remediation=remediation))
            continue
        helper_module_aliases.add(alias.asname or imported_parts[-1])
    return faults, helper_module_aliases


def _is_allowed_sibling_public_surface(
    *, parent_package_parts: tuple[str, ...], imported_parts: tuple[str, ...]
) -> bool:
    if len(imported_parts) <= len(parent_package_parts) + 1:
        return True
    sibling_tail: tuple[str, ...] = imported_parts[len(parent_package_parts) + 1 :]
    if not sibling_tail:
        return True
    if sibling_tail[0] in _public_role_names:
        return True
    return (
        sibling_tail[0] == RoleName.MAIN and len(sibling_tail) >= _minimum_public_surface_tail_parts
    )


def _allowed_sibling_dependencies(current_subpackage_name: str) -> frozenset[str]:
    if current_subpackage_name in _owned_role_names:
        return frozenset({RoleName.HELPERS})
    if current_subpackage_name == RoleName.HELPERS:
        return frozenset({RoleName.CLASSES})
    return frozenset()


def _has_internal_segment(parts: tuple[str, ...]) -> bool:
    return any(part in _internal_surface_segments() for part in parts)


def _public_surface_segments() -> frozenset[str]:
    return frozenset({*_owned_role_names, _init_module_name})


def _internal_surface_segments() -> frozenset[str]:
    return frozenset({RoleName.HELPERS, RoleName.SHARED})


def _is_helper_module_path(parts: tuple[str, ...]) -> bool:
    return RoleName.HELPERS in parts


def _is_private_class_name(name: str) -> bool:
    return len(name) > 1 and name.startswith("_") and name[1].isupper()


def _attribute_base_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return _attribute_base_name(node.value)
    return None
