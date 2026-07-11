"""Tests rule-family types."""

from __future__ import annotations

from enum import StrEnum


class SftCode(StrEnum):
    """Stable tests rule codes."""

    INIT_MODULE_EMPTY = "SFT001"
    ABSOLUTE_IMPORTS = "SFT002"
    TEST_TYPES_DESCRIPTION = "SFT003"
    TEST_TYPES_EXPECTED_FIELD = "SFT004"
    LOCAL_TEST_TYPES_IMPORT = "SFT005"
    TEST_FILE_NAME = "SFT006"
    TEST_FUNCTION_NAME = "SFT007"
    DATACLASS_PARAMETRIZE = "SFT008"
    ACCEPTS_TEST_CASE = "SFT009"
    TEST_CASE_ANNOTATION = "SFT010"
    EXPECTED_FIELD_ASSERTION = "SFT011"
    PARAMETRIZE_ARGUMENTS = "SFT012"
    PARAMETRIZE_TEST_CASE = "SFT013"
    PARAMETRIZE_IDS = "SFT014"
    NO_MODULE_TEST_CASE_LISTS = "SFT015"
    INLINE_PARAMETRIZE_VALUES = "SFT016"
    INLINE_PARAMETRIZE_SEQUENCE = "SFT021"
    NONEMPTY_PARAMETRIZE_VALUES = "SFT022"
    NO_DICT_TEST_CASES = "SFT023"
    LOCAL_TEST_CASE_CONSTRUCTORS = "SFT024"
    DESCRIPTION_LAMBDA_IDS = "SFT025"
    LOCAL_TEST_TYPES_FILE = "SFT026"
    NO_TOP_LEVEL_HELPERS = "SFT027"
    TEST_LAYOUT = "SFT028"
    TEST_SCOPE = "SFT029"
    TEST_MIRRORED_ROOT = "SFT030"
    SRC_MIRROR_DEPTH = "SFT031"
    SRC_PACKAGE_EXISTS = "SFT032"
    SRC_AREA_EXISTS = "SFT033"
    SCRIPTS_MIRROR_DEPTH = "SFT034"
    SCRIPTS_AREA_EXISTS = "SFT035"
    NO_IF_IN_TESTS = "SFT036"
    PRIVATE_CONSTANT_ORDER = "SFT037"
    NO_COMPLEX_COMPREHENSIONS = "SFT038"


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
