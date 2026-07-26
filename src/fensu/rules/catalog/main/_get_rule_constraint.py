"""Read one canonical fixed rule constraint."""

from __future__ import annotations

from fensu.rules.catalog.constants import CORE_RULES
from fensu.rules.catalog.exceptions import RuleConstraintNotFoundError


def get_rule_constraint(*, code: str, name: str) -> tuple[str, ...]:
    """Return one exhaustive fixed value set from the core catalogue."""

    for rule in CORE_RULES:
        if rule.code != code:
            continue
        for constraint in rule.constraints:
            if constraint.name == name:
                return constraint.values
    raise RuleConstraintNotFoundError(f"rule {code} has no {name} constraint")
