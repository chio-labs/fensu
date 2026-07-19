"""Public custom equivalent of native helper parameter-mutation policy."""

import ast

from strata import Family, Fault, RuleContext, rule


@rule(
    code="XCS102",
    family=Family.CUSTOM,
    slug="parameter-mutation-in-phase-helpers-equivalent",
    message="helpers must return values instead of mutating parameters",
    remediation="Return a new or updated value so dataflow remains visible to the caller.",
)
def parameter_mutation_in_phase_helpers_equivalent(
    *, module: ast.Module, ctx: RuleContext
) -> list[Fault]:
    """Express SFS102 through public position and parameter-mutation facts."""

    del module
    if not ctx.in_role("helpers"):
        return []
    return [
        ctx.fault_at(location=fact.location)
        for fact in ctx.facts.parameter_mutations()
        if not fact.dunder and not fact.setter
    ]
