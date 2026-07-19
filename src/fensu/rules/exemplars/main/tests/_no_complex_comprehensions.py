"""Public custom equivalent of native test-comprehension policy."""

import ast

from fensu import Family, Fault, RuleContext, ScopeName, rule


@rule(
    code="XCT106",
    family=Family.CUSTOM,
    slug="test-no-complex-comprehensions-equivalent",
    message="nested or multi-generator comprehensions hide control flow and data shapes",
    remediation=(
        "Extract a named helper when the transformation has a coherent purpose. For one-off "
        "local logic, use simple statements with named intermediate values instead of nested "
        "comprehension control flow."
    ),
)
def test_no_complex_comprehensions_equivalent(
    *, module: ast.Module, ctx: RuleContext
) -> list[Fault]:
    """Express FFT106 through public scope and control-flow facts."""

    del module
    if ctx.scope() is not ScopeName.TEST:
        return []
    return [ctx.fault_at(location=item) for item in ctx.facts.complex_comprehensions()]
