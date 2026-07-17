"""Import-path helpers for layer boundary rules."""

from __future__ import annotations

from strata.analysis.models import ImportFact
from strata.discovery.constants import STRUCTURAL_MODULE_PART_TO_NAME
from strata.discovery.types import RoleName
from strata.rules.layers.models import ModuleOwnership

_public_surface_role_names: frozenset[str] = frozenset(
    {
        RoleName.MAIN,
        RoleName.CLASSES,
        RoleName.MODELS,
        RoleName.TYPES,
        RoleName.CONSTANTS,
        RoleName.EXCEPTIONS,
    }
)


def classify_module_ownership(
    *, module_parts: tuple[str, ...], initializer: bool
) -> ModuleOwnership:
    """Classify a module by its first structural role after the package root."""

    package: str | None = module_parts[0] if module_parts else None
    role_index: int | None = next(
        (
            index
            for index, part in enumerate(module_parts[1:], start=1)
            if part in STRUCTURAL_MODULE_PART_TO_NAME
        ),
        None,
    )
    if role_index is not None:
        owner_prefix: tuple[str, ...] = module_parts[1:role_index]
        first_role: str | None = STRUCTURAL_MODULE_PART_TO_NAME[module_parts[role_index]]
        tail: tuple[str, ...] = module_parts[role_index + 1 :]
    else:
        owner_end: int = len(module_parts) if initializer else max(1, len(module_parts) - 1)
        owner_prefix = module_parts[1:owner_end]
        first_role = None
        tail = module_parts[owner_end:]
    return ModuleOwnership(
        package=package,
        owner_prefix=owner_prefix,
        domain=owner_prefix[0] if owner_prefix else None,
        first_role=first_role,
        tail=tail,
    )


def normalized_import_targets(
    *,
    fact: ImportFact,
    current_module_parts: tuple[str, ...],
    current_initializer: bool,
) -> tuple[tuple[str, ...], ...]:
    """Return absolute, structurally resolvable targets for one import statement."""

    if not fact.from_import:
        return tuple(alias.imported_parts for alias in fact.aliases)
    if fact.relative_level == 0:
        return (fact.module_parts,) if fact.module_parts else ()
    if not fact.module_parts:
        return ()
    current_package: tuple[str, ...] = (
        current_module_parts if current_initializer else current_module_parts[:-1]
    )
    parent_count: int = fact.relative_level - 1
    if parent_count > len(current_package):
        return ()
    base: tuple[str, ...] = current_package[: len(current_package) - parent_count]
    return ((*base, *fact.module_parts),)


def import_module_targets(
    *,
    fact: ImportFact,
    current_module_parts: tuple[str, ...],
    current_initializer: bool,
) -> tuple[tuple[str, ...], ...]:
    """Return module targets including resolvable from-import submodules."""

    bases: tuple[tuple[str, ...], ...] = normalized_import_targets(
        fact=fact,
        current_module_parts=current_module_parts,
        current_initializer=current_initializer,
    )
    targets: list[tuple[str, ...]] = list(bases)
    if fact.from_import:
        for base in bases:
            targets.extend((*base, *alias.imported_parts) for alias in fact.aliases)
    return tuple(dict.fromkeys(targets))


def is_domain_private_main_entry(ownership: ModuleOwnership) -> bool:
    """Return whether ownership identifies a single-underscore main entry module."""

    module_name: str = ownership.tail[-1] if ownership.tail else ""
    return (
        ownership.first_role is RoleName.MAIN
        and module_name.startswith("_")
        and not module_name.startswith("__")
    )


def is_public_main_entry(ownership: ModuleOwnership) -> bool:
    """Return whether ownership identifies an ordinary public main entry module."""

    module_name: str = ownership.tail[-1] if ownership.tail else ""
    return (
        ownership.first_role is RoleName.MAIN
        and bool(module_name)
        and not module_name.startswith("_")
    )


def is_sibling_internal_import(*, current: ModuleOwnership, target: ModuleOwnership) -> bool:
    """Return whether an import reaches into a sibling package's internals."""

    return (
        current.package is not None
        and current.package == target.package
        and current.domain is not None
        and current.domain == target.domain
        and current.owner != target.owner
        and not _is_public_surface(target)
    )


def is_cross_package_internal_import(*, current: ModuleOwnership, target: ModuleOwnership) -> bool:
    """Return whether an import reaches into another package's internal structure."""

    return (
        current.package is not None
        and current.package == target.package
        and current.domain is not None
        and target.domain is not None
        and current.domain != target.domain
        and not _is_public_surface(target)
    )


def import_path_targets_tooling(
    *, imported_parts: tuple[str, ...], tooling_packages: frozenset[str]
) -> bool:
    """Return whether an absolute import targets configured tooling."""

    return bool(imported_parts) and imported_parts[0] in tooling_packages


def _is_public_surface(ownership: ModuleOwnership) -> bool:
    return ownership.first_role in _public_surface_role_names
