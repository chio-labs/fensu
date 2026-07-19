"""Tests rule catalogue entries."""

from __future__ import annotations

import ast

from fensu.rules.authoring.models import Fault, RuleSpec
from fensu.rules.authoring.types import Family, RuleContext
from fensu.rules.tests._helpers.checks import test_faults
from fensu.rules.tests._helpers.metadata import test_rule_details
from fensu.rules.tests.types import FftCode


def test_rules() -> tuple[RuleSpec, ...]:
    """Build tests family rules."""

    return tuple(_rule(code=code, slug=code.name.lower().replace("_", "-")) for code in FftCode)


def _rule(*, code: FftCode, slug: str) -> RuleSpec:
    def check(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
        del module
        return test_faults(ctx=ctx, code=code)

    details: tuple[str, str] = test_rule_details(code)
    message: str = details[0]
    remediation: str | None = details[1]
    return RuleSpec(
        code=code,
        family=Family.TESTS,
        slug=slug,
        message=message,
        check=check,
        remediation=remediation,
    )
