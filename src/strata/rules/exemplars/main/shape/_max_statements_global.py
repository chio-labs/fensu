"""Public custom equivalent of native global statement-count policy."""

import ast

from strata import Family, Fault, RuleContext, Threshold, rule


@rule(
    code="XCS011",
    family=Family.CUSTOM,
    slug="max-statements-global-equivalent",
    message="functions must stay below the global statement limit",
    remediation=(
        "Split the function at a meaningful phase boundary with explicit inputs and outputs."
    ),
)
def max_statements_global_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express SFS011 through public function facts and threshold policy."""

    del module
    limit: int = ctx.threshold(name=Threshold.MAX_STATEMENTS_GLOBAL)
    return [
        ctx.fault_at(
            location=fact.location, message=f"function has {fact.statement_count} statements"
        )
        for fact in ctx.facts.functions().functions
        if fact not in (ctx.facts.functions().top_level if ctx.is_main_module() else ())
        and fact.statement_count > limit
    ]
