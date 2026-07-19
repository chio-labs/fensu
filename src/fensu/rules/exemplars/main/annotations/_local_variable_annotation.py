"""Public-API custom equivalent of native local-variable annotation policy."""

from __future__ import annotations

import ast

from fensu import Family, Fault, RuleContext, rule


@rule(
    code="XCP103",
    family=Family.CUSTOM,
    slug="local-variable-annotation-equivalent",
    message=(
        "local variables must define type annotations on first binding unless assigned a scalar "
        "literal"
    ),
    remediation=(
        "Annotate first bindings whose type is not evident from a number, string, bool, bytes, or "
        "f-string literal."
    ),
)
def local_variable_annotation_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express FFA103 entirely through the public custom-rule API."""

    del module
    return [
        ctx.fault_at(
            location=fact.location,
            message=(
                f"local variable '{fact.name}' must define a type annotation on first binding"
            ),
        )
        for fact in ctx.facts.annotations().locals
        if not fact.scalar_literal
    ]
