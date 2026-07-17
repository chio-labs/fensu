"""Rule check functions for the layers family."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from strata.analysis.models import AttributeReferenceFact, ImportFact, ReferenceFacts
from strata.analysis.types import Analysis
from strata.discovery.constants import (
    HELPERS_DIRECTORY_NAME,
    INIT_MODULE_FILE_NAME,
    PYTHON_FILE_SUFFIX,
)
from strata.discovery.types import ScopeName
from strata.rules.authoring.models import Fault
from strata.rules.authoring.types import RuleContext
from strata.rules.layers._helpers.imports import (
    classify_module_ownership,
    import_module_targets,
    import_path_targets_tooling,
    is_cross_package_internal_import,
    is_domain_private_main_entry,
    is_public_main_entry,
    is_sibling_internal_import,
    normalized_import_targets,
)
from strata.rules.layers.models import ModuleOwnership

_wildcard_import_name: str = "*"


@dataclass(frozen=True, slots=True)
class _ProjectModule:
    path: Path
    scope: ScopeName
    module_parts: tuple[str, ...]
    ownership: ModuleOwnership
    references: ReferenceFacts


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
    key: str = "layers.import_target:" + ".".join(module_parts)
    return ctx._memoize(
        key=key,
        operation=lambda: _computed_import_target(ctx=ctx, module_parts=module_parts),
    )


def _computed_import_target(*, ctx: RuleContext, module_parts: tuple[str, ...]) -> ModuleOwnership:
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


def no_cross_domain_private_main_imports(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Reject imports of domain-private main entries from outside their domain."""

    del module
    current_module_parts: tuple[str, ...] = ctx.module_parts()
    current_initializer: bool = ctx.path.name == INIT_MODULE_FILE_NAME
    current: ModuleOwnership = classify_module_ownership(
        module_parts=current_module_parts,
        initializer=current_initializer,
    )
    faults: list[Fault] = []
    for fact in ctx.facts.references().imports:
        for imported_parts in import_module_targets(
            fact=fact,
            current_module_parts=current_module_parts,
            current_initializer=current_initializer,
        ):
            target: ModuleOwnership = classify_module_ownership(
                module_parts=imported_parts,
                initializer=False,
            )
            if (
                is_domain_private_main_entry(target)
                and _module_exists(ctx=ctx, module_parts=imported_parts)
                and not _shares_domain(current=current, target=target)
            ):
                faults.append(
                    ctx.fault_at(
                        location=fact.location,
                        message=(
                            f"import '{'.'.join(imported_parts)}' reaches a domain-private main "
                            "entry"
                        ),
                    )
                )
                break
    return faults


def public_main_entry_external_use(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Require every public main entry to have an importer outside its domain."""

    del module
    modules: tuple[_ProjectModule, ...] = _project_modules(ctx=ctx)
    public_entries: dict[tuple[str, ...], _ProjectModule] = {
        item.module_parts: item
        for item in modules
        if item.scope is ScopeName.ROOT
        and item.path.suffix == PYTHON_FILE_SUFFIX
        and item.path.name != INIT_MODULE_FILE_NAME
        and item.ownership.domain is not None
        and is_public_main_entry(item.ownership)
    }
    externally_used: set[tuple[str, ...]] = {
        tuple(module_name.split("."))
        for module_name in ctx.project.entrypoint_modules(requester=ctx.path)
    }
    for importer in modules:
        initializer: bool = importer.path.name == INIT_MODULE_FILE_NAME
        for fact in importer.references.imports:
            for imported_parts in import_module_targets(
                fact=fact,
                current_module_parts=importer.module_parts,
                current_initializer=initializer,
            ):
                target: _ProjectModule | None = public_entries.get(imported_parts)
                if target is not None and _outside_domain(importer=importer, target=target):
                    externally_used.add(imported_parts)
    return [
        ctx.path_fault(
            path=entry.path,
            message="public main entry has no importer outside its owning domain",
        )
        for module_parts, entry in sorted(
            public_entries.items(), key=lambda item: str(item[1].path)
        )
        if module_parts not in externally_used
    ]


def _project_modules(*, ctx: RuleContext) -> tuple[_ProjectModule, ...]:
    modules: list[_ProjectModule] = []
    for scope in (ScopeName.ROOT, ScopeName.TOOLING):
        for root in ctx.scope_roots(scope):
            paths: set[Path] = set()
            for pattern in ("*.py", "*.pyi"):
                paths.update(
                    ctx.project.glob(
                        requester=ctx.path,
                        path=root,
                        pattern=pattern,
                        recursive=True,
                    )
                )
            for path in sorted(paths):
                analysis: Analysis | None = ctx.project.analysis(requester=ctx.path, path=path)
                if analysis is None:
                    continue
                module_parts: tuple[str, ...] = _module_parts(path=path, root=root)
                modules.append(
                    _ProjectModule(
                        path=path,
                        scope=scope,
                        module_parts=module_parts,
                        ownership=classify_module_ownership(
                            module_parts=module_parts,
                            initializer=path.name == INIT_MODULE_FILE_NAME,
                        ),
                        references=analysis.facts.references(),
                    )
                )
    return tuple(modules)


def _module_parts(*, path: Path, root: Path) -> tuple[str, ...]:
    relative_parts: tuple[str, ...] = path.relative_to(root.parent).parts
    parts: tuple[str, ...] = (*relative_parts[:-1], path.stem)
    return parts[:-1] if parts[-1] == INIT_MODULE_FILE_NAME.removesuffix(".py") else parts


def _module_exists(*, ctx: RuleContext, module_parts: tuple[str, ...]) -> bool:
    if not module_parts:
        return False
    for root in ctx.scope_roots(ScopeName.ROOT):
        if root.name != module_parts[0]:
            continue
        relative: Path = Path(*module_parts[1:])
        if ctx.project.is_file(requester=ctx.path, path=root / relative.with_suffix(".py")):
            return True
    return False


def _shares_domain(*, current: ModuleOwnership, target: ModuleOwnership) -> bool:
    return (
        current.package is not None
        and current.package == target.package
        and current.domain is not None
        and current.domain == target.domain
    )


def _outside_domain(*, importer: _ProjectModule, target: _ProjectModule) -> bool:
    return importer.scope is ScopeName.TOOLING or not _shares_domain(
        current=importer.ownership,
        target=target.ownership,
    )


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
            if event.from_import and HELPERS_DIRECTORY_NAME in event.module_parts:
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
                    if HELPERS_DIRECTORY_NAME not in alias.imported_parts:
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
