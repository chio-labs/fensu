"""Public-API custom equivalent of native parameter annotation policy."""

from __future__ import annotations

import ast

from fensu import Family, Fault, RuleContext, rule


@rule(
    code="XCP001",
    family=Family.CUSTOM,
    slug="parameter-annotation-equivalent",
    message="function parameters must define type annotations",
    remediation="Annotate every parameter with the value type accepted by the function.",
)
def parameter_annotation_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express FFA001 entirely through the public custom-rule API."""

    del module
    return [
        ctx.fault_at(
            location=fact.location,
            message=f"function parameter '{fact.name}' must define a type annotation",
        )
        for fact in ctx.facts.annotations().parameters
    ]
