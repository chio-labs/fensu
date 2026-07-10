"""Naming contract rule catalogue entries."""

from __future__ import annotations

from strata.rules.authoring.models import RuleSpec
from strata.rules.authoring.types import Family
from strata.rules.naming.helpers.checks import validator_must_not_return
from strata.rules.naming.types import NamingCode


def contract_rules() -> tuple[RuleSpec, ...]:
    """Build naming contract rules."""

    return (
        RuleSpec(
            code=NamingCode.VALIDATOR_MUST_NOT_RETURN,
            family=Family.NAMING,
            slug="validator-must-not-return",
            message="functions under no-return naming contracts must not return values",
            remediation=(
                "Raise on invalid input and return None implicitly from validate_, enforce_, or "
                "check_ functions."
            ),
            check=validator_must_not_return,
        ),
    )
