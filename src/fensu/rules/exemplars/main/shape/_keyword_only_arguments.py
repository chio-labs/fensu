"""Public custom equivalent of native keyword-only argument policy."""

import ast

from fensu import Family, Fault, RuleContext, Threshold, rule


@rule(
    code="XCS120",
    family=Family.CUSTOM,
    slug="keyword-only-arguments-equivalent",
    message="functions beyond the parameter threshold must be entirely keyword-only",
    remediation=(
        "Insert * before the first non-receiver parameter so every call argument names its meaning."
    ),
)
def keyword_only_arguments_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express FFS120 through public function facts and threshold policy."""

    del module
    limit: int = ctx.threshold(name=Threshold.MAX_POSITIONAL_ARGS)
    return [
        ctx.fault_at(
            location=fact.location,
            message=(
                f"function with {fact.parameter_count} parameters has "
                f"{fact.positional_parameter_count} positional parameters"
            ),
        )
        for fact in ctx.facts.functions().functions
        if not fact.dunder and fact.parameter_count > limit and fact.positional_parameter_count > 0
    ]
