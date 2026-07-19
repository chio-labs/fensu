"""Public custom equivalent of native unnamed-string policy."""

import ast

from strata import Family, Fault, RuleContext, rule


@rule(
    code="XCH007",
    family=Family.CUSTOM,
    slug="no-unnamed-string-decisions-equivalent",
    message="string literals must not directly control comparison behavior",
    remediation=(
        "Name the decision value in constants.py or compare against an enum member so the branch "
        "expresses the concept it represents."
    ),
)
def no_unnamed_string_decisions_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express SFH007 through public hygiene facts."""

    del module
    return [ctx.fault_at(location=item) for item in ctx.facts.hygiene().unnamed_string_decisions]
