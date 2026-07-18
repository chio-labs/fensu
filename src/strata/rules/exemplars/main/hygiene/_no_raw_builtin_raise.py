"""Public custom equivalent of native raw-raise policy."""

import ast

from strata import Family, Fault, RuleContext, rule


@rule(
    code="XCH003",
    family=Family.CUSTOM,
    slug="no-raw-builtin-raise-equivalent",
    message="runtime code must raise structured errors instead of raw built-in exceptions",
    remediation=(
        "Raise a domain-specific exception from exceptions.py with a stable actionable message."
    ),
)
def no_raw_builtin_raise_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express SFH003 through public hygiene facts."""

    del module
    return [ctx.fault_at(location=item) for item in ctx.facts.hygiene().raw_builtin_raises]
