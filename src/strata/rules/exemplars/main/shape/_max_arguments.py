"""Public custom equivalent of native function argument-count policy."""

import ast

from strata import Family, Fault, RuleContext, Threshold, rule


@rule(
    code="XCS010",
    family=Family.CUSTOM,
    slug="max-arguments-equivalent",
    message="functions must stay below the configured argument limit",
    remediation="Reduce the function's responsibility or group cohesive inputs into a typed model.",
)
def max_arguments_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express SFS010 through public function facts and threshold policy."""

    del module
    limit: int = ctx.threshold(name=Threshold.MAX_ARGUMENTS)
    return [
        ctx.fault_at(
            location=fact.location, message=f"function has {fact.parameter_count} parameters"
        )
        for fact in ctx.facts.functions().functions
        if fact.parameter_count > limit
    ]
