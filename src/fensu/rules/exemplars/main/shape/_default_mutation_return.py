"""Public custom equivalent of native parameter-mutation return policy."""

import ast

from fensu import Family, Fault, RuleContext, rule
from fensu.rules.exemplars.types import ExemplarFunctionKind


@rule(
    code="XCS110",
    family=Family.CUSTOM,
    slug="default-mutation-return-equivalent",
    message="functions that mutate parameters must return every mutated parameter",
    remediation=(
        "Return each mutated parameter explicitly, or avoid parameter mutation and return a new "
        "value."
    ),
)
def default_mutation_return_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express FFS110 through public parameter-mutation facts."""

    del module
    exempt_kinds: tuple[str, ...] = ctx.constraint(name="exempt_function_kinds")
    return [
        ctx.fault_at(location=fact.location)
        for fact in ctx.facts.parameter_mutations()
        if not (fact.dunder and ExemplarFunctionKind.DUNDER in exempt_kinds)
        and not (fact.setter and ExemplarFunctionKind.SETTER in exempt_kinds)
        and not fact.returned
    ]
