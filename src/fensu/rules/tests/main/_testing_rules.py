"""Tests rule catalogue entries."""

from __future__ import annotations

from fensu.rules.authoring.models import RuleSpec
from fensu.rules.authoring.types import Family
from fensu.rules.tests._helpers.metadata import test_rule_details
from fensu.rules.tests.types import FftCode


def test_rules() -> tuple[RuleSpec, ...]:
    """Build tests family rules."""

    return tuple(_rule(code=code, slug=code.name.lower().replace("_", "-")) for code in FftCode)


def _rule(*, code: FftCode, slug: str) -> RuleSpec:
    details: tuple[str, str] = test_rule_details(code)
    message: str = details[0]
    remediation: str | None = details[1]
    return RuleSpec(
        code=code,
        family=Family.TESTS,
        slug=slug,
        message=message,
        remediation=remediation,
    )
