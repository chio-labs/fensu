"""Helpers for shape catalogue tests."""

from __future__ import annotations

from strata.rules.authoring.models import RuleSpec
from strata.rules.shape.constants import SFS_RULES


def shape_rule_by_code(*, rule_code: str) -> RuleSpec:
    """Return the shape rule with the requested code."""

    rules_by_code: dict[str, RuleSpec] = {rule.code: rule for rule in SFS_RULES}
    return rules_by_code[rule_code]
