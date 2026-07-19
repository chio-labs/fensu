"""Public-API custom equivalent of native class-attribute annotation policy."""

from __future__ import annotations

import ast

from fensu import Family, Fault, RuleContext, rule


@rule(
    code="XCP102",
    family=Family.CUSTOM,
    slug="class-attribute-annotation-equivalent",
    message="class attributes must define type annotations",
    remediation="Annotate the class attribute where it is first assigned.",
)
def class_attribute_annotation_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express FFA102 entirely through the public custom-rule API."""

    del module
    return [
        ctx.fault_at(
            location=fact.location,
            message=f"class attribute '{fact.name}' must define a type annotation",
        )
        for fact in ctx.facts.annotations().class_attributes
    ]
