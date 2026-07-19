"""Public custom equivalent of native main statement-count policy."""

import ast

from fensu import Family, Fault, RuleContext, Threshold, rule


@rule(
    code="XCS001",
    family=Family.CUSTOM,
    slug="too-many-statements-equivalent",
    message="main functions must stay phase-shaped and below the statement limit",
    remediation="Extract cohesive phases into helpers that return explicit result models.",
)
def too_many_statements_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express FFS001 through public function facts and threshold policy."""

    del module
    if not ctx.is_main_module():
        return []
    limit: int = ctx.threshold(name=Threshold.MAX_STATEMENTS)
    return [
        ctx.fault_at(
            location=fact.location, message=f"function has {fact.statement_count} statements"
        )
        for fact in ctx.facts.functions().top_level
        if fact.statement_count > limit
    ]
