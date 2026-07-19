"""Public custom equivalent of sibling internal import policy."""

import ast

from fensu import Family, Fault, RuleContext, rule
from fensu.rules.exemplars._helpers.import_ownership import (
    is_public,
    normalized_targets,
    ownership,
    target_initializer,
)
from fensu.rules.exemplars.types import ExemplarLayerPathName, ImportOwnership


@rule(
    code="XCL101",
    family=Family.CUSTOM,
    slug="no-sibling-package-internals-equivalent",
    message="subpackage code must not import sibling internals",
    remediation="Publish the dependency through the owning sibling's main/ entry or role files.",
)
def no_sibling_package_internals_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express FFL101 through public references and project existence."""

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
                and current.domain == target.domain
                and current.owner != target.owner
                and not is_public(target)
            ):
                faults.append(
                    ctx.fault_at(
                        location=fact.location,
                        message=f"import '{'.'.join(parts)}' reaches into sibling internals",
                    )
                )
                break
    return faults
