"""Public-fact import ownership helpers used by custom layer exemplars."""

from pathlib import Path

from fensu import ImportFact, RuleContext, ScopeName
from fensu.rules.exemplars.types import ExemplarRoleName, ImportOwnership

_STRUCTURAL_ROLES: frozenset[str] = frozenset(
    {"main", "_helpers", "classes", "models", "types", "constants", "exceptions"}
)
_PUBLIC_ROLES: frozenset[str] = frozenset(
    {"main", "classes", "models", "types", "constants", "exceptions"}
)


def ownership(*, parts: tuple[str, ...], initializer: bool) -> ImportOwnership:
    """Classify one module using only stable structural path names."""

    role_index: int | None = next(
        (index for index, part in enumerate(parts[1:], start=1) if part in _STRUCTURAL_ROLES),
        None,
    )
    if role_index is None:
        owner_end: int = len(parts) if initializer else max(1, len(parts) - 1)
        owner_prefix: tuple[str, ...] = parts[1:owner_end]
        role: str | None = None
        tail: tuple[str, ...] = parts[owner_end:]
    else:
        owner_prefix = parts[1:role_index]
        role = "helpers" if parts[role_index] == ExemplarRoleName.HELPERS else parts[role_index]
        tail = parts[role_index + 1 :]
    package: str | None = parts[0] if parts else None
    return ImportOwnership(
        package=package,
        owner=(() if package is None else (package,)) + owner_prefix,
        domain=owner_prefix[0] if owner_prefix else None,
        role=role,
        tail=tail,
    )


def normalized_targets(
    *, fact: ImportFact, current_parts: tuple[str, ...], initializer: bool
) -> tuple[tuple[str, ...], ...]:
    """Resolve absolute and relative import bases."""

    if not fact.from_import:
        return tuple(alias.imported_parts for alias in fact.aliases)
    if fact.relative_level == 0:
        return (fact.module_parts,) if fact.module_parts else ()
    if not fact.module_parts:
        return ()
    current_package: tuple[str, ...] = current_parts if initializer else current_parts[:-1]
    parent_count: int = fact.relative_level - 1
    if parent_count > len(current_package):
        return ()
    return ((*current_package[: len(current_package) - parent_count], *fact.module_parts),)


def target_initializer(*, ctx: RuleContext, parts: tuple[str, ...]) -> bool:
    """Observe whether a target resolves to a package initializer."""

    return ctx.project.exists(
        requester=ctx.path,
        path=ctx.scope_root().parent.joinpath(*parts) / "__init__.py",
    )


def target_module_exists(*, ctx: RuleContext, parts: tuple[str, ...]) -> bool:
    """Observe whether a target resolves to a runtime module."""

    for root in ctx.scope_roots(ScopeName.ROOT):
        if parts and root.name == parts[0]:
            relative: Path = Path(*parts[1:])
            if ctx.project.is_file(requester=ctx.path, path=root / relative.with_suffix(".py")):
                return True
    return False


def is_public(ownership_value: ImportOwnership) -> bool:
    """Return whether a target uses an approved public role."""

    return ownership_value.role in _PUBLIC_ROLES
