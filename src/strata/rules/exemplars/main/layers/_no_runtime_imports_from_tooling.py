"""Public custom equivalent of native runtime-to-tooling import policy."""

import ast

from strata import Family, Fault, RuleContext, ScopeName, rule


@rule(
    code="XCL301",
    family=Family.CUSTOM,
    slug="no-runtime-imports-from-tooling-equivalent",
    message="runtime code must not import from tooling modules",
    remediation=(
        "Move reusable logic into the runtime package or keep the dependency inside tooling."
    ),
)
def no_runtime_imports_from_tooling_equivalent(
    *, module: ast.Module, ctx: RuleContext
) -> list[Fault]:
    """Express SFL301 through public scope, layout, and reference APIs."""

    del module
    if ctx.scope() is not ScopeName.ROOT:
        return []
    tooling_packages: frozenset[str] = frozenset(
        root.name for root in ctx.scope_roots(ScopeName.TOOLING)
    )
    faults: list[Fault] = []
    for fact in ctx.facts.references().imports:
        if fact.from_import:
            if (
                fact.relative_level == 0
                and fact.module_parts
                and fact.module_parts[0] in tooling_packages
            ):
                faults.append(ctx.fault_at(location=fact.location))
        elif any(
            alias.imported_parts and alias.imported_parts[0] in tooling_packages
            for alias in fact.aliases
        ):
            faults.append(ctx.fault_at(location=fact.location))
    return faults
