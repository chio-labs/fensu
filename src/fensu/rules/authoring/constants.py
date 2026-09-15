"""Private authoring metadata constants."""

from __future__ import annotations

import re

from fensu.rules.authoring.types import Missing

CUSTOM_RULE_REGISTRATIONS_CACHE_KEY: str = "fensu.ffr707.custom-rule-registrations"
MISSING: Missing = Missing.VALUE
OPTION_NAME_PATTERN: re.Pattern[str] = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
MINIMUM_OPTION_INTEGER: int = -(2**63)
MAXIMUM_OPTION_INTEGER: int = 2**63 - 1
PROJECT_ROOT: str = "."
WINDOWS_PATH_SEPARATOR: str = "\\"
CURRENT_PATH_PART: str = "."
PARENT_PATH_PART: str = ".."
LEGACY_RULE_PARAMETER_COUNT: int = 2
LEGACY_RULE_PARAMETER_NAMES: tuple[str, str] = ("module", "ctx")
TYPED_RULE_KEYWORD_PARAMETER_COUNT: int = 2
VAR_POSITIONAL_FLAG: int = 0x04
VAR_KEYWORD_FLAG: int = 0x08

_RULE_SPEC_ATTRIBUTE: str = "__fensu_rule_spec__"
