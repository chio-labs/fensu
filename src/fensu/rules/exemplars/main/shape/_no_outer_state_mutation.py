"""Public custom equivalent of native outer-state mutation policy."""

import ast

from fensu import Family, Fault, RuleContext, rule


@rule(
    code="XCS130",
    family=Family.CUSTOM,
    slug="no-outer-state-mutation-equivalent",
    message="functions must not mutate module-global or closure-captured state",
    remediation=(
        "Pass state explicitly and return the updated value instead of mutating outer scope."
    ),
)
def no_outer_state_mutation_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express FFS130 through public outer-state facts."""

    del module
    return [ctx.fault_at(location=fact.location) for fact in ctx.facts.outer_state_mutations()]
