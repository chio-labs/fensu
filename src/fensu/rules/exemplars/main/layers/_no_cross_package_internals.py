"""Public custom equivalent of cross-package internal import policy."""

import ast

from fensu import (
    Family,
    Fault,
    ModuleNode,
    ModuleVisibility,
    ProjectPath,
    RuleContext,
    rule,
)
from fensu.rules.exemplars._helpers.import_ownership import (
    is_public,
    ownership,
    ownership_start,
)
from fensu.rules.exemplars.types import ExemplarLayerPathName, ImportOwnership


@rule(
    code="XCL102",
    family=Family.CUSTOM,
    slug="no-cross-package-internals-equivalent",
    message="cross-package imports must use public surfaces, not helpers or internals",
    remediation=(
        "Import from classes, models, types, constants, exceptions, or a thin main/ entry."
    ),
)
def no_cross_package_internals_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express FFL102 through public architecture graph facts."""

    del module
    current: ModuleNode | None = ctx.graph.node(
        ProjectPath(ctx.path.relative_to(ctx.repo_root).as_posix())
    )
    if current is None:
        return []
    current_parts: tuple[str, ...] = tuple(current.module.split("."))
    current_ownership: ImportOwnership = ownership(
        parts=current_parts,
        initializer=ctx.path.name == ExemplarLayerPathName.INIT,
        owner_start=ownership_start(ctx=ctx, parts=current_parts),
    )
    faults: list[Fault] = []
    faulted_statements: set[tuple[int, int]] = set()
    for edge in ctx.graph.imports(current):
        statement: tuple[int, int] = (edge.location.line, edge.location.column)
        if statement in faulted_statements:
            continue
        target: ModuleNode | None = edge.target
        target_module: str | None = edge.module
        if target_module is None:
            continue
        target_ownership: ImportOwnership = ownership(
            parts=tuple(target_module.split(".")),
            initializer=False,
            owner_start=ownership_start(ctx=ctx, parts=tuple(target_module.split("."))),
        )
        target_internal: bool = (
            target.visibility is ModuleVisibility.INTERNAL
            if target is not None
            else not is_public(target_ownership)
        )
        if (
            current.module.partition(".")[0] == target_module.partition(".")[0]
            and current_ownership.domain is not None
            and target_ownership.domain is not None
            and (
                current_ownership.ownership_root != target_ownership.ownership_root
                or current_ownership.domain != target_ownership.domain
            )
            and target_internal
        ):
            parts: list[str] = target_module.split(".")
            package: str = ".".join(parts[: ownership_start(ctx=ctx, parts=tuple(parts)) + 1])
            faults.append(
                ctx.fault_at(
                    location=edge.location,
                    message=(
                        f"import '{target_module}' reaches into internal structure of '{package}'"
                    ),
                )
            )
            faulted_statements.add(statement)
    return faults
