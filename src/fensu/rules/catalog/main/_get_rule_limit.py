"""Read one canonical fixed rule limit."""

from __future__ import annotations

from fensu.rules.authoring.models import RuleSpec
from fensu.rules.catalog.exceptions import RuleConstraintNotFoundError
from fensu.rules.catalog.main._get_rule_spec import get_rule_spec


def get_rule_limit(*, code: str, name: str) -> int:
    """Return one fixed numeric limit from the core catalogue."""

    rule: RuleSpec = get_rule_spec(code=code)
    for limit in rule.limits:
        if limit.name == name:
            return limit.value
    raise RuleConstraintNotFoundError(f"rule {code} has no {name} limit")
