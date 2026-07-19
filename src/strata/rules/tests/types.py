"""Tests rule-family types."""

from __future__ import annotations

from enum import StrEnum


class SftCode(StrEnum):
    """Stable tests rule codes."""

    TEST_LAYOUT = "SFT001"
    TEST_SCOPE = "SFT002"
    TEST_MIRRORED_ROOT = "SFT003"
    SRC_MIRROR_DEPTH = "SFT004"
    SRC_PACKAGE_EXISTS = "SFT005"
    SRC_AREA_EXISTS = "SFT006"
    SCRIPTS_MIRROR_DEPTH = "SFT007"
    SCRIPTS_AREA_EXISTS = "SFT008"
    INIT_MODULE_EMPTY = "SFT101"
    ABSOLUTE_IMPORTS = "SFT102"
    NO_TOP_LEVEL_HELPERS = "SFT103"
    NO_IF_IN_TESTS = "SFT104"
    PRIVATE_CONSTANT_ORDER = "SFT105"
    NO_COMPLEX_COMPREHENSIONS = "SFT106"
    TEST_TYPES_DESCRIPTION = "SFT201"
    TEST_TYPES_EXPECTED_FIELD = "SFT202"
    LOCAL_TEST_TYPES_IMPORT = "SFT203"
    LOCAL_TEST_TYPES_FILE = "SFT204"
    TEST_FILE_NAME = "SFT301"
    TEST_FUNCTION_NAME = "SFT302"
    DATACLASS_PARAMETRIZE = "SFT401"
    ACCEPTS_TEST_CASE = "SFT402"
    TEST_CASE_ANNOTATION = "SFT403"
    EXPECTED_FIELD_ASSERTION = "SFT404"
    PARAMETRIZE_ARGUMENTS = "SFT405"
    PARAMETRIZE_TEST_CASE = "SFT406"
    PARAMETRIZE_IDS = "SFT407"
    INLINE_PARAMETRIZE_VALUES = "SFT408"
    NONEMPTY_PARAMETRIZE_VALUES = "SFT411"
    NO_DICT_TEST_CASES = "SFT412"
    LOCAL_TEST_CASE_CONSTRUCTORS = "SFT413"
    DESCRIPTION_LAMBDA_IDS = "SFT414"


class TestPathName(StrEnum):
    """Filesystem names with test-layout semantics."""

    ROOT_SURFACE = "__root__"
    INIT_MODULE = "__init__.py"
    CONFTEST = "conftest.py"
    HELPERS = "helpers.py"
    TEST_HELPERS = "_test_helpers.py"
    TEST_TYPES = "_test_types.py"
    SCENARIO_MODELS = "scenario_models.py"


class TestSymbol(StrEnum):
    """Python symbols with test-convention semantics."""

    DESCRIPTION = "description"
    TEST_CASE = "test_case"
    IDS = "ids"
    CASE = "case"
    PARAMETRIZE = "pytest.mark.parametrize"
    TEST_CASES = "TEST_CASES"


class TestScope(StrEnum):
    """Supported test suite scopes."""

    UNIT = "unit"
    INTEGRATION = "integration"
    E2E = "e2e"
