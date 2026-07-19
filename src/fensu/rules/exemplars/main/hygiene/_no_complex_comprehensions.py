"""Public custom equivalent of native tooling-comprehension policy."""

import ast

from fensu import Family, Fault, RuleContext, ScopeName, rule


@rule(
    code="XCH006",
    family=Family.CUSTOM,
    slug="no-complex-comprehensions-in-tooling-equivalent",
    message="nested or multi-generator comprehensions hide control flow and data shapes",
    remediation=(
        "Extract a named helper when the transformation has a coherent purpose. For one-off "
        "local logic, use simple statements with named intermediate values instead of nested "
        "comprehension control flow."
    ),
)
def no_complex_comprehensions_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express FFH006 through public scope and control-flow APIs."""

    del module
    if ctx.scope() is not ScopeName.TOOLING:
        return []
    return [ctx.fault_at(location=item) for item in ctx.facts.complex_comprehensions()]
