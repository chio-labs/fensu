"""Public custom equivalent of native swallowed-probe policy."""

import ast

from fensu import Family, Fault, RuleContext, rule


@rule(
    code="XCH005",
    family=Family.CUSTOM,
    slug="no-swallowed-exception-probe-equivalent",
    message="runtime code must not swallow broad exceptions as existence probe answers",
    remediation=(
        "Use an explicit metadata or existence check, or catch only the expected exception and "
        "preserve failures."
    ),
)
def no_swallowed_exception_probe_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express FFH005 through public hygiene facts."""

    del module
    return [ctx.fault_at(location=item) for item in ctx.facts.hygiene().swallowed_exception_probes]
