"""Public custom equivalent of cross-package internal import policy."""

import ast

from strata import Family, Fault, RuleContext, rule
from strata.rules.exemplars._helpers.import_ownership import (
    is_public,
    normalized_targets,
    ownership,
    target_initializer,
)
from strata.rules.exemplars.types import ExemplarLayerPathName, ImportOwnership


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
    """Express SFL102 through public references and project existence."""

    del module
    current: ImportOwnership = ownership(
        parts=ctx.module_parts(), initializer=ctx.path.name == ExemplarLayerPathName.INIT
    )
    faults: list[Fault] = []
    for fact in ctx.facts.references().imports:
        for parts in normalized_targets(
            fact=fact,
            current_parts=ctx.module_parts(),
            initializer=ctx.path.name == ExemplarLayerPathName.INIT,
        ):
            target: ImportOwnership = ownership(
                parts=parts, initializer=target_initializer(ctx=ctx, parts=parts)
            )
            if (
                current.package == target.package
                and current.domain is not None
                and target.domain is not None
                and current.domain != target.domain
                and not is_public(target)
            ):
                package: str = ".".join(parts[:2])
                faults.append(
                    ctx.fault_at(
                        location=fact.location,
                        message=(
                            f"import '{'.'.join(parts)}' reaches into internal structure of "
                            f"'{package}'"
                        ),
                    )
                )
                break
    return faults
