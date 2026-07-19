"""Public custom equivalent of native main local-count policy."""

import ast

from strata import Family, Fault, RuleContext, Threshold, rule


@rule(
    code="XCS003",
    family=Family.CUSTOM,
    slug="too-many-locals-equivalent",
    message="main functions must not juggle too many local variables",
    remediation="Let each extracted phase own its intermediates and return one structured result.",
)
def too_many_locals_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express SFS003 through public function facts and threshold policy."""

    del module
    if not ctx.is_main_module():
        return []
    limit: int = ctx.threshold(name=Threshold.MAX_LOCALS)
    return [
        ctx.fault_at(
            location=fact.location,
            message=f"function defines {fact.assigned_local_count} local variables",
        )
        for fact in ctx.facts.functions().top_level
        if fact.assigned_local_count > limit
    ]
