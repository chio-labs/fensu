"""Rule check functions for the layers family."""

from __future__ import annotations

import ast

from strata.analysis.models import AttributeReferenceFact, ImportFact, ReferenceFacts
from strata.discovery.constants import INIT_MODULE_FILE_NAME
from strata.discovery.types import ScopeName
from strata.rules.authoring.models import Fault
from strata.rules.authoring.types import RuleContext
from strata.rules.layers.helpers.imports import (
    classify_module_ownership,
    import_path_targets_tooling,
    is_cross_package_internal_import,
    is_sibling_internal_import,
    normalized_import_targets,
)
from strata.rules.layers.models import ModuleOwnership

_wildcard_import_name: str = "*"
_helper_role_name: str = "helpers"


def absolute_imports_only(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Reject relative imports."""

    del module
    return [
        ctx.fault_at(location=fact.location)
        for fact in ctx.facts.references().imports
        if fact.from_import and fact.relative_level > 0
    ]


def no_star_imports(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Reject wildcard imports that hide imported names from boundary analysis."""

    del module
    faults: list[Fault] = []
    for fact in ctx.facts.references().imports:
        if fact.from_import and any(
            alias.imported_name == _wildcard_import_name for alias in fact.aliases
        ):
            faults.append(ctx.fault_at(location=fact.location))
    return faults


def no_sibling_package_internals(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Reject imports that reach into sibling package internals."""

    del module
    current_module_parts: tuple[str, ...] = ctx.module_parts()
    current_initializer: bool = ctx.path.name == INIT_MODULE_FILE_NAME
    current: ModuleOwnership = classify_module_ownership(
        module_parts=current_module_parts, initializer=current_initializer
    )
    faults: list[Fault] = []
    for fact in ctx.facts.references().imports:
        for imported_parts in normalized_import_targets(
            fact=fact,
            current_module_parts=current_module_parts,
            current_initializer=current_initializer,
        ):
            target: ModuleOwnership = _classify_import_target(ctx=ctx, module_parts=imported_parts)
            if is_sibling_internal_import(current=current, target=target):
                faults.append(
                    ctx.fault_at(
                        location=fact.location,
                        message=(
                            f"import '{'.'.join(imported_parts)}' reaches into sibling internals"
                        ),
                    )
                )
                break
    return faults


def no_cross_package_internals(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Reject imports that reach into another package's internal structure."""

    del module
    current_module_parts: tuple[str, ...] = ctx.module_parts()
    current_initializer: bool = ctx.path.name == INIT_MODULE_FILE_NAME
    current: ModuleOwnership = classify_module_ownership(
        module_parts=current_module_parts, initializer=current_initializer
    )
    faults: list[Fault] = []
    for fact in ctx.facts.references().imports:
        for imported_parts in normalized_import_targets(
            fact=fact,
            current_module_parts=current_module_parts,
            current_initializer=current_initializer,
        ):
            target: ModuleOwnership = _classify_import_target(ctx=ctx, module_parts=imported_parts)
            if is_cross_package_internal_import(current=current, target=target):
                target_package: str = ".".join(imported_parts[:2])
                faults.append(
                    ctx.fault_at(
                        location=fact.location,
                        message=(
                            f"import '{'.'.join(imported_parts)}' reaches into internal structure "
                            f"of '{target_package}'"
                        ),
                    )
                )
                break
    return faults


def _classify_import_target(*, ctx: RuleContext, module_parts: tuple[str, ...]) -> ModuleOwnership:
    return classify_module_ownership(
        module_parts=module_parts,
        initializer=ctx.project.exists(
            requester=ctx.path,
            path=ctx.scope_root().parent.joinpath(*module_parts) / INIT_MODULE_FILE_NAME,
        ),
    )


def no_internal_public_surface_imports(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Reject internal imports routed through the bare runtime package surface."""

    del module
    if ctx.scope() is not ScopeName.ROOT or (
        ctx.path.name == INIT_MODULE_FILE_NAME and len(ctx.relative_parts()) == 1
    ):
        return []
    package_name: str = ctx.module_parts()[0]
    faults: list[Fault] = []
    for fact in ctx.facts.references().imports:
        if fact.from_import and fact.relative_level == 0 and fact.module_parts == (package_name,):
            faults.append(ctx.fault_at(location=fact.location))
        elif not fact.from_import and any(
            alias.imported_name == package_name for alias in fact.aliases
        ):
            faults.append(ctx.fault_at(location=fact.location))
    return faults


def no_cross_file_helper_private_classes(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Reject cross-file use of helper-local private classes."""

    del module
    return _private_helper_reference_faults(ctx=ctx, facts=ctx.facts.references())


def no_runtime_imports_from_tooling(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Reject runtime code importing from the conventional tooling package."""

    del module
    if ctx.scope() is not ScopeName.ROOT:
        return []
    tooling_packages: frozenset[str] = frozenset(
        root.name for root in ctx.scope_roots(ScopeName.TOOLING)
    )
    faults: list[Fault] = []
    for fact in ctx.facts.references().imports:
        if fact.from_import and fact.relative_level == 0:
            if import_path_targets_tooling(
                imported_parts=fact.module_parts,
                tooling_packages=tooling_packages,
            ):
                faults.append(ctx.fault_at(location=fact.location))
        elif not fact.from_import:
            for alias in fact.aliases:
                if import_path_targets_tooling(
                    imported_parts=alias.imported_parts,
                    tooling_packages=tooling_packages,
                ):
                    faults.append(ctx.fault_at(location=fact.location))
                    break
    return faults


def _private_helper_reference_faults(*, ctx: RuleContext, facts: ReferenceFacts) -> list[Fault]:
    message: str = "helper-private classes are file-local details; move shared classes to classes/"
    remediation: str = "If another module needs this class, move it to the owning classes/ package."
    faults: list[Fault] = []
    helper_module_aliases: set[str] = set()
    for event in facts.events:
        if isinstance(event, ImportFact):
            if event.from_import and _helper_role_name in event.module_parts:
                for alias in event.aliases:
                    if _is_private_class_name(alias.imported_name):
                        faults.append(
                            ctx.fault_at(
                                location=event.location, message=message, remediation=remediation
                            )
                        )
                    else:
                        helper_module_aliases.add(alias.bound_name)
            elif not event.from_import:
                for alias in event.aliases:
                    if _helper_role_name not in alias.imported_parts:
                        continue
                    if alias.imported_parts and _is_private_class_name(alias.imported_parts[-1]):
                        faults.append(
                            ctx.fault_at(
                                location=event.location, message=message, remediation=remediation
                            )
                        )
                    else:
                        helper_module_aliases.add(alias.bound_name)
        elif (
            isinstance(event, AttributeReferenceFact)
            and _is_private_class_name(event.attribute_name)
            and event.base_name in helper_module_aliases
        ):
            faults.append(
                ctx.fault_at(location=event.location, message=message, remediation=remediation)
            )
    return faults


def _is_private_class_name(name: str) -> bool:
    return len(name) > 1 and name.startswith("_") and name[1].isupper()
