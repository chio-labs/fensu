"""Stable constants for test convention checks."""

import re

TEST_NAME_PATTERN: re.Pattern[str] = re.compile(r"^test_given_.+_when_.+_then_.+$")
VALID_TEST_SCOPES: frozenset[str] = frozenset({"unit", "integration", "e2e"})
RUNTIME_PACKAGE_NAME: str = "strata"
ROOT_AREA_NAME: str = "__root__"
