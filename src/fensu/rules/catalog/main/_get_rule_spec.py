"""Read one canonical core rule specification."""

from __future__ import annotations

from fensu.rules.authoring.models import RuleSpec
from fensu.rules.catalog.constants import CORE_RULES
from fensu.rules.catalog.exceptions import RuleConstraintNotFoundError


def get_rule_spec(*, code: str) -> RuleSpec:
    """Return the canonical core specification for one exact code."""

    for rule in CORE_RULES:
        if rule.code == code:
            return rule
    raise RuleConstraintNotFoundError(f"core rule {code} is not defined")
