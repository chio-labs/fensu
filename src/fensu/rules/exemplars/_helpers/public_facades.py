"""Public-equivalent implementation of facade import-direction policy."""

from __future__ import annotations

import ast
from pathlib import Path

from fensu import Fault, ImportFact, RuleContext, ScopeName
from fensu.analysis.main.is_public_facade import is_public_facade_source
from fensu.analysis.types import Analysis

_INIT_FILE: str = "__init__.py"
_INIT_STEM: str = "__init__"
_FACADE_MODULE_PARTS: int = 2


def public_facade_import_direction_impl(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Reject production imports that point back through root facade modules."""

    del module
    if ctx.scope() is not ScopeName.ROOT:
        return []
    root: Path = ctx.scope_root()
    package_name: str = root.name
    current_parts: tuple[str, ...] = (
        package_name,
        *(part.removesuffix(".py") for part in ctx.relative_parts()),
    )
    if current_parts[-1] == _INIT_STEM:
        current_parts = current_parts[:-1]
    faults: list[Fault] = []
    for fact in ctx.facts.references().imports:
        targets: tuple[tuple[str, ...], ...] = _import_targets(
            fact=fact,
            current_parts=current_parts,
            initializer=ctx.path.name == _INIT_FILE,
        )
        candidates: tuple[tuple[str, ...], ...] = tuple(
            target
            for target in targets
            if len(target) == _FACADE_MODULE_PARTS and target[0] == package_name
        )
        if not any(
            _path_is_public_facade(
                ctx=ctx,
                path=root / f"{target[1]}.py",
                package_name=package_name,
            )
            for target in candidates
        ):
            continue
        faults.append(
            ctx.fault_at(
                location=fact.location,
                message="runtime modules must import the facade's owning domain directly",
            )
        )
    return faults


def _path_is_public_facade(*, ctx: RuleContext, path: Path, package_name: str) -> bool:
    analysis: Analysis | None = ctx.project.analysis(requester=ctx.path, path=path)
    return analysis is not None and is_public_facade_source(
        source=analysis.text.source, package_name=package_name
    )


def _import_targets(
    *, fact: ImportFact, current_parts: tuple[str, ...], initializer: bool
) -> tuple[tuple[str, ...], ...]:
    if not fact.from_import:
        return tuple(tuple(alias.imported_parts) for alias in fact.aliases)
    package: tuple[str, ...] = current_parts if initializer else current_parts[:-1]
    if fact.relative_level == 0:
        bases: tuple[tuple[str, ...], ...] = (
            (tuple(fact.module_parts),) if fact.module_parts else ()
        )
    else:
        parents: int = fact.relative_level - 1
        if parents > len(package):
            return ()
        base: tuple[str, ...] = package[: len(package) - parents]
        bases = ((*base, *fact.module_parts),)
    targets: list[tuple[str, ...]] = list(bases)
    for base in bases:
        targets.extend((*base, *alias.imported_parts) for alias in fact.aliases)
    return tuple(dict.fromkeys(targets))
