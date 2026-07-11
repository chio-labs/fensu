"""Import-path helpers for layer boundary rules."""

from __future__ import annotations

import ast
from pathlib import Path

from strata.discovery.core.types import RoleName

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

    relative_parts: tuple[str, ...] = path.relative_to(repo_root).parts
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
