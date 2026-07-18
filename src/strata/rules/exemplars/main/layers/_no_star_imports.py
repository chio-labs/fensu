"""Public custom equivalent of native star-import policy."""

import ast

from strata import Family, Fault, RuleContext, ScopeName, rule


@rule(
    code="XCL002",
    family=Family.CUSTOM,
    slug="no-star-imports-equivalent",
    message="star imports hide names from dependency-boundary analysis",
    remediation="Import each required name explicitly.",
)
def no_star_imports_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express SFL002 through public scope and reference facts."""

    del module
    if ctx.scope() is ScopeName.TEST:
        return []
    faults: list[Fault] = []
    for fact in ctx.facts.references().imports:
        if fact.from_import and any(
            _is_star_import_name(alias.imported_name) for alias in fact.aliases
        ):
            faults.append(ctx.fault_at(location=fact.location))
    return faults


def _is_star_import_name(name: str) -> bool:
    return name.startswith("*") and not name.removeprefix("*")
