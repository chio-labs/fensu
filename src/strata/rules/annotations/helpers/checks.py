"""Rule check functions for the annotations family."""

from __future__ import annotations

import ast

from strata.rules.annotations.classes.annotation_visitor import AnnotationVisitor
from strata.rules.annotations.types import AnnotationCode
from strata.rules.authoring.models import Fault
from strata.rules.authoring.types import RuleContext


def annotation_faults(*, module: ast.Module, ctx: RuleContext, code: AnnotationCode) -> list[Fault]:
    """Collect annotation faults for a single annotation rule code."""

    return AnnotationVisitor(ctx=ctx, code=code).collect(module)
