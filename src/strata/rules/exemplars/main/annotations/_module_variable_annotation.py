"""Public-API custom equivalent of native module-variable annotation policy."""

from __future__ import annotations

import ast

from strata import Family, Fault, RuleContext, rule


@rule(
    code="XCP101",
    family=Family.CUSTOM,
    slug="module-variable-annotation-equivalent",
    message="module-level variables must define type annotations",
    remediation="Add an explicit annotation to the first module-level assignment.",
)
def module_variable_annotation_equivalent(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Express SFA101 entirely through the public custom-rule API."""

    del module
    return [
        ctx.fault_at(
            location=fact.location,
            message=f"module-level variable '{fact.name}' must define a type annotation",
        )
        for fact in ctx.facts.annotations().module_variables
    ]
