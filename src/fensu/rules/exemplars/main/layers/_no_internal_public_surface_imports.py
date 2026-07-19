"""Public custom equivalent of native internal public-surface import policy."""

import ast

from fensu import Family, Fault, RuleContext, ScopeName, rule
from fensu.rules.exemplars.types import ExemplarLayerPathName


@rule(
    code="XCL103",
    family=Family.CUSTOM,
    slug="no-internal-public-surface-imports-equivalent",
    message="internal code must import from the owning module, not the bare package",
    remediation="Import from the concrete owning module below the package surface.",
)
def no_internal_public_surface_imports_equivalent(
    *, module: ast.Module, ctx: RuleContext
) -> list[Fault]:
    """Express FFL103 through public position and reference APIs."""

    del module
    if (
        ctx.scope() is not ScopeName.ROOT
        or (
            ctx.domain() == ExemplarLayerPathName.RULES
            and ctx.subdomain() == ExemplarLayerPathName.EXEMPLARS
        )
        or (ctx.path.name == ExemplarLayerPathName.INIT and len(ctx.relative_parts()) == 1)
    ):
        return []
    package_name: str = ctx.module_parts()[0]
    faults: list[Fault] = []
    for fact in ctx.facts.references().imports:
        if fact.from_import:
            if fact.relative_level == 0 and fact.module_parts == (package_name,):
                faults.append(ctx.fault_at(location=fact.location))
        elif any(alias.imported_name == package_name for alias in fact.aliases):
            faults.append(ctx.fault_at(location=fact.location))
    return faults
