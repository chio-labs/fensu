"""Rule check functions for the annotations family."""

from __future__ import annotations

import ast

from strata.rules.annotations.types import AnnotationCode
from strata.rules.authoring.models import Fault
from strata.rules.authoring.types import RuleContext


def annotation_faults(*, module: ast.Module, ctx: RuleContext, code: AnnotationCode) -> list[Fault]:
    """Collect annotation faults for a single annotation rule code."""

    if code == AnnotationCode.PARAMETER_ANNOTATION:
        return [
            ctx.fault_at(
                location=fact.location,
                message=f"function parameter '{fact.name}' must define a type annotation",
            )
            for fact in ctx.facts.annotations().parameters
        ]
    if code == AnnotationCode.RETURN_ANNOTATION:
        return [
            ctx.fault_at(
                location=fact.location,
                message=f"function '{fact.name}' must define a return type annotation",
            )
            for fact in ctx.facts.annotations().returns
        ]
    if code == AnnotationCode.LOCAL_VARIABLE_ANNOTATION:
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
    if code == AnnotationCode.MODULE_VARIABLE_ANNOTATION:
        return [
            ctx.fault_at(
                location=fact.location,
                message=f"module-level variable '{fact.name}' must define a type annotation",
            )
            for fact in ctx.facts.annotations().module_variables
        ]
    return [
        ctx.fault_at(
            location=fact.location,
            message=f"class attribute '{fact.name}' must define a type annotation",
        )
        for fact in ctx.facts.annotations().class_attributes
    ]
