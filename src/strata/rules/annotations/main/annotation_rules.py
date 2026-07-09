"""Annotation rule catalogue entries."""

from __future__ import annotations

import ast

from strata.rules.annotations.helpers.checks import annotation_faults
from strata.rules.annotations.types import AnnotationCode
from strata.rules.authoring.models import Fault, RuleSpec
from strata.rules.authoring.types import Family, RuleContext


def annotation_rules() -> tuple[RuleSpec, ...]:
    """Build annotation family rules."""

    return (
        _rule(
            code=AnnotationCode.PARAMETER_ANNOTATION,
            slug="parameter-annotation",
            message="function parameters must define type annotations",
        ),
        _rule(
            code=AnnotationCode.RETURN_ANNOTATION,
            slug="return-annotation",
            message="functions must define return type annotations",
        ),
        _rule(
            code=AnnotationCode.MODULE_VARIABLE_ANNOTATION,
            slug="module-variable-annotation",
            message="module-level variables must define type annotations",
        ),
        _rule(
            code=AnnotationCode.CLASS_ATTRIBUTE_ANNOTATION,
            slug="class-attribute-annotation",
            message="class attributes must define type annotations",
        ),
        _rule(
            code=AnnotationCode.LOCAL_VARIABLE_ANNOTATION,
            slug="local-variable-annotation",
            message="local variables must define type annotations on first binding",
        ),
    )


def _rule(*, code: AnnotationCode, slug: str, message: str) -> RuleSpec:
    def check(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
        return annotation_faults(module=module, ctx=ctx, code=code)

    return RuleSpec(code=code, family=Family.ANNOTATIONS, slug=slug, message=message, check=check)
