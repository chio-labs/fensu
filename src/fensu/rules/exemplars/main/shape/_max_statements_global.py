"""Public custom equivalent of native global statement-count policy."""

import ast

from fensu import Fault, RuleContext, Threshold
from fensu.rules.exemplars._helpers.equivalent_rule import equivalent_rule


@equivalent_rule(
    core_code="FFS011",
    code="XCS011",
    slug="max-statements-global-equivalent",
)
def max_statements_global_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express FFS011 through public function facts and threshold policy."""

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
