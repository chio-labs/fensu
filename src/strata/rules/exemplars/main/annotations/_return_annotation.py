"""Public-API custom equivalent of native return annotation policy."""

from __future__ import annotations

import ast

from strata import Family, Fault, RuleContext, rule


@rule(
    code="XCP002",
    family=Family.CUSTOM,
    slug="return-annotation-equivalent",
    message="functions must define return type annotations",
    remediation="Declare the returned value type, using None when the function returns no value.",
)
def return_annotation_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express SFA002 entirely through the public custom-rule API."""

    del module
    return [
        ctx.fault_at(
            location=fact.location,
            message=f"function '{fact.name}' must define a return type annotation",
        )
        for fact in ctx.facts.annotations().returns
    ]
