"""Public custom equivalent of native shape-comprehension policy."""

import ast

from fensu import Family, Fault, RuleContext, rule


@rule(
    code="XCS131",
    family=Family.CUSTOM,
    slug="no-complex-comprehensions-equivalent",
    message="nested or multi-generator comprehensions hide control flow and data shapes",
    remediation=(
        "Extract a named helper when the transformation has a coherent purpose. For one-off "
        "local logic, use simple statements with named intermediate values instead of nested "
        "comprehension control flow."
    ),
)
def no_complex_comprehensions_shape_equivalent(
    *, module: ast.Module, ctx: RuleContext
) -> list[Fault]:
    """Express FFS131 through public control-flow facts."""

    del module
    return [ctx.fault_at(location=item) for item in ctx.facts.complex_comprehensions()]
