"""Resolve one rule option through the canonical authoring validator."""

from __future__ import annotations

from fensu.rules.authoring._helpers.options import get_rule_option_value as _get_value
from fensu.rules.authoring.models import RuleOption
from fensu.rules.authoring.types import RuleOptionValue


def get_rule_option_value(
    *, option: RuleOption[object], value: object, authoring: bool = False
) -> RuleOptionValue:
    """Return one validated canonical immutable rule-option value."""

    return _get_value(option=option, value=value, authoring=authoring)
