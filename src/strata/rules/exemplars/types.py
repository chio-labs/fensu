"""Type-layer vocabulary shared by public custom test-rule equivalents."""

from enum import StrEnum


class ExemplarLayerPathName(StrEnum):
    """Path names used for local layer-policy routing."""

    INIT = "__init__.py"
    RULES = "rules"
    EXEMPLARS = "exemplars"


class ExemplarTestPathName(StrEnum):
    """Test support filenames used for local-only scope routing."""

    INIT = "__init__.py"
    CONFTEST = "conftest.py"
    HELPERS = "helpers.py"
    TEST_HELPERS = "_test_helpers.py"
    TEST_TYPES = "_test_types.py"


class ExemplarTestSymbol(StrEnum):
    """Pytest and test-case names used by local policy."""

    DESCRIPTION = "description"
    EXPECTED_PREFIX = "expected_"
    TEST_CASE = "test_case"


class ExemplarTestLimit(StrEnum):
    """Fixed syntax cardinalities used by local pytest policy."""

    MINIMUM_PARAMETRIZE_ARGUMENTS = "2"
