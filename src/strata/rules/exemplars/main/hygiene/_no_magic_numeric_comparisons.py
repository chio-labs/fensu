"""Public custom equivalent of native magic-number policy."""

import ast

from strata import Family, Fault, RuleContext, rule


@rule(
    code="XCH008",
    family=Family.CUSTOM,
    slug="no-magic-numeric-comparisons-equivalent",
    message="non-canonical numeric literals must not directly control comparisons",
    remediation=(
        "Name the threshold or sentinel in constants.py and compare against that name; only -1, "
        "0, and 1 are self-explanatory comparison values."
    ),
)
def no_magic_numeric_comparisons_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express SFH008 through public hygiene facts."""

    del module
    return [ctx.fault_at(location=item) for item in ctx.facts.hygiene().magic_numeric_comparisons]
