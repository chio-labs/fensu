"""Public custom equivalent of native main call-count policy."""

import ast

from strata import Family, Fault, RuleContext, Threshold, rule


@rule(
    code="XCS002",
    family=Family.CUSTOM,
    slug="too-many-distinct-calls-equivalent",
    message="main functions must not coordinate too many distinct callees",
    remediation=(
        "Group related work into named phase helpers and keep main/ as a short ordered flow."
    ),
)
def too_many_distinct_calls_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express SFS002 through public function facts and threshold policy."""

    del module
    if not ctx.is_main_module():
        return []
    limit: int = ctx.threshold(name=Threshold.MAX_DISTINCT_CALLS)
    return [
        ctx.fault_at(
            location=fact.location,
            message=f"function calls {fact.distinct_call_count} distinct functions",
        )
        for fact in ctx.facts.functions().top_level
        if fact.distinct_call_count > limit
    ]
