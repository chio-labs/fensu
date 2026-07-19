"""Public custom equivalent of native mutable result-model policy."""

import ast

from strata import Family, Fault, RuleContext, rule


@rule(
    code="XCS201",
    family=Family.CUSTOM,
    slug="mutable-result-model-equivalent",
    message="dataclass result models must be frozen",
    remediation="Declare the shared result model with @dataclass(frozen=True).",
)
def mutable_result_model_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express SFS201 through public position and dataclass facts."""

    del module
    if not ctx.in_role("models"):
        return []
    return [
        ctx.fault_at(location=fact.location)
        for fact in ctx.facts.dataclasses()
        if fact.shape_candidate and not fact.frozen
    ]
