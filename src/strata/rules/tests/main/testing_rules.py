"""Tests rule catalogue entries."""

from __future__ import annotations

import ast

from strata.rules.authoring.models import Fault, RuleSpec
from strata.rules.authoring.types import Family, RuleContext
from strata.rules.tests.helpers.checks import test_faults
from strata.rules.tests.helpers.metadata import test_rule_details
from strata.rules.tests.types import SftCode


def test_rules() -> tuple[RuleSpec, ...]:
    """Build tests family rules."""

    return tuple(_rule(code=code, slug=code.name.lower().replace("_", "-")) for code in SftCode)


def _rule(*, code: SftCode, slug: str) -> RuleSpec:
    def check(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
        return test_faults(module=module, ctx=ctx, code=code)

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
