"""Public custom equivalent of native runtime-assert policy."""

import ast

from strata import Family, Fault, RuleContext, rule


@rule(
    code="XCH004",
    family=Family.CUSTOM,
    slug="no-assert-in-runtime-equivalent",
    message="runtime code must not use assert for invariants; raise a structured error",
    remediation="Replace assert with an explicit guard that raises a domain-specific exception.",
)
def no_assert_in_runtime_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express SFH004 through public hygiene facts."""

    del module
    return [ctx.fault_at(location=item) for item in ctx.facts.hygiene().assertions]
