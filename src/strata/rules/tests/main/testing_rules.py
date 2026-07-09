"""Tests rule catalogue entries."""

from __future__ import annotations

import ast

from strata.rules.authoring.models import Fault, RuleSpec
from strata.rules.authoring.types import Family, RuleContext
from strata.rules.tests.helpers.checks import test_faults
from strata.rules.tests.types import SftCode


def test_rules() -> tuple[RuleSpec, ...]:
    """Build tests family rules."""

    return tuple(_rule(code=code, slug=code.name.lower().replace("_", "-")) for code in SftCode)


def _rule(*, code: SftCode, slug: str) -> RuleSpec:
    def check(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
        return test_faults(module=module, ctx=ctx, code=code)

    details: tuple[str, str | None] = _details(code)
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


def _details(code: SftCode) -> tuple[str, str | None]:
    if code == SftCode.NO_IF_IN_TESTS:
        return (
            "test bodies must not contain conditional control flow",
            "Split behavioral branches into parametrized cases and move conditional setup or "
            "selection into local test helpers.",
        )
    if code == SftCode.NO_COMPLEX_COMPREHENSIONS:
        return (
            "nested or multi-generator comprehensions hide control flow and data shapes",
            "Rewrite this as ordinary statements with named intermediate values. Use explicit "
            "loops when needed, and extract a helper only when the transformation is a distinct "
            "operation.",
        )
    return f"test convention violation ({code.value})", None
