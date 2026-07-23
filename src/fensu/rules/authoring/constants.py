"""Private authoring metadata constants."""

from __future__ import annotations

import re

from fensu.rules.authoring.types import Missing

CUSTOM_RULE_REGISTRATIONS_CACHE_KEY: str = "fensu.ffr707.custom-rule-registrations"
MISSING: Missing = Missing.VALUE
OPTION_NAME_PATTERN: re.Pattern[str] = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
MINIMUM_OPTION_INTEGER: int = -(2**63)
MAXIMUM_OPTION_INTEGER: int = 2**63 - 1

_RULE_SPEC_ATTRIBUTE: str = "__fensu_rule_spec__"
