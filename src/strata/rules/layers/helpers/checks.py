"""Rule check functions for the layers family."""

from __future__ import annotations

import ast

from strata.discovery.core.constants import INIT_MODULE_FILE_NAME
from strata.discovery.core.types import ScopeName
from strata.rules.authoring.models import Fault
from strata.rules.authoring.types import RuleContext
from strata.rules.layers.helpers.imports import (
    import_alias_parts,
    import_from_parts,
    import_path_targets_tooling,
    is_cross_package_internal_import,
    is_sibling_internal_import,
    module_parts_for_path,
    private_helper_class_import_faults,
)

_wildcard_import_name: str = "*"


def absolute_imports_only(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Reject relative imports."""

    faults: list[Fault] = []
    for node in ctx.nodes(ast.ImportFrom):
        if isinstance(node, ast.ImportFrom) and node.level > 0:
            faults.append(ctx.fault(node))
    return faults


def no_star_imports(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Reject wildcard imports that hide imported names from boundary analysis."""

    faults: list[Fault] = []
    for node in ctx.nodes(ast.ImportFrom):
        if isinstance(node, ast.ImportFrom) and any(
            alias.name == _wildcard_import_name for alias in node.names
        ):
            faults.append(ctx.fault(node))
    return faults


def no_sibling_package_internals(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Reject imports that reach into sibling package internals."""

    current_module_parts: tuple[str, ...] = module_parts_for_path(
        path=ctx.path, repo_root=ctx.repo_root
    )
    faults: list[Fault] = []
    for node in (*ctx.nodes(ast.ImportFrom), *ctx.nodes(ast.Import)):
        if isinstance(node, ast.ImportFrom) and node.level == 0:
            imported_parts: tuple[str, ...] = import_from_parts(node)
            if is_sibling_internal_import(
                current_module_parts=current_module_parts, imported_parts=imported_parts
            ):
                faults.append(
                    ctx.fault(
                        node,
                        message=(
                            f"import '{'.'.join(imported_parts)}' reaches into sibling internals"
                        ),
                    )
                )
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imported_parts = import_alias_parts(alias)
                if is_sibling_internal_import(
                    current_module_parts=current_module_parts,
                    imported_parts=imported_parts,
                ):
                    faults.append(
                        ctx.fault(
                            node,
                            message=(
                                f"import '{'.'.join(imported_parts)}' reaches into sibling "
                                "internals"
                            ),
                        )
                    )
                    break
    return faults


def no_cross_package_internals(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Reject imports that reach into another package's internal structure."""

    current_module_parts: tuple[str, ...] = module_parts_for_path(
        path=ctx.path, repo_root=ctx.repo_root
    )
    faults: list[Fault] = []
    for node in (*ctx.nodes(ast.ImportFrom), *ctx.nodes(ast.Import)):
        if isinstance(node, ast.ImportFrom) and node.level == 0:
            imported_parts: tuple[str, ...] = import_from_parts(node)
            if is_cross_package_internal_import(
                current_module_parts=current_module_parts, imported_parts=imported_parts
            ):
                target_package: str = ".".join(imported_parts[:2])
                faults.append(
                    ctx.fault(
                        node,
                        message=(
                            f"import '{'.'.join(imported_parts)}' reaches into internal structure "
                            f"of '{target_package}'"
                        ),
                    )
                )
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imported_parts = import_alias_parts(alias)
                if is_cross_package_internal_import(
                    current_module_parts=current_module_parts,
                    imported_parts=imported_parts,
                ):
                    target_package = ".".join(imported_parts[:2])
                    faults.append(
                        ctx.fault(
                            node,
                            message=(
                                f"import '{'.'.join(imported_parts)}' reaches into internal "
                                f"structure of '{target_package}'"
                            ),
                        )
                    )
                    break
    return faults


def no_internal_public_surface_imports(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Reject internal imports routed through the bare runtime package surface."""

    if ctx.scope() is not ScopeName.ROOT or (
        ctx.path.name == INIT_MODULE_FILE_NAME and len(ctx.relative_parts()) == 1
    ):
        return []
    package_name: str = ctx.path.parents[len(ctx.relative_parts()) - 1].name
    faults: list[Fault] = []
    for node in (*ctx.nodes(ast.ImportFrom), *ctx.nodes(ast.Import)):
        if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module == package_name:
            faults.append(ctx.fault(node))
        elif isinstance(node, ast.Import) and any(
            alias.name == package_name for alias in node.names
        ):
            faults.append(ctx.fault(node))
    return faults


def no_cross_file_helper_private_classes(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Reject cross-file use of helper-local private classes."""

    return private_helper_class_import_faults(
        module=module,
        ctx=ctx,
        message="helper-private classes are file-local details; move shared classes to classes/",
        remediation="If another module needs this class, move it to the owning classes/ package.",
    )


def no_runtime_imports_from_tooling(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Reject runtime code importing from the conventional tooling package."""

    if ctx.scope() is not ScopeName.ROOT:
        return []
    faults: list[Fault] = []
    for node in (*ctx.nodes(ast.ImportFrom), *ctx.nodes(ast.Import)):
        if isinstance(node, ast.ImportFrom) and node.level == 0:
            if import_path_targets_tooling(imported_parts=import_from_parts(node)):
                faults.append(ctx.fault(node))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if import_path_targets_tooling(imported_parts=import_alias_parts(alias)):
                    faults.append(ctx.fault(node))
                    break
    return faults
