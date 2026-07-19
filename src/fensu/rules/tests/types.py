"""Tests rule-family types."""

from __future__ import annotations

from enum import StrEnum


class FftCode(StrEnum):
    """Stable tests rule codes."""

    TEST_LAYOUT = "FFT001"
    TEST_SCOPE = "FFT002"
    TEST_MIRRORED_ROOT = "FFT003"
    SRC_MIRROR_DEPTH = "FFT004"
    SRC_PACKAGE_EXISTS = "FFT005"
    SRC_AREA_EXISTS = "FFT006"
    SCRIPTS_MIRROR_DEPTH = "FFT007"
    SCRIPTS_AREA_EXISTS = "FFT008"
    INIT_MODULE_EMPTY = "FFT101"
    ABSOLUTE_IMPORTS = "FFT102"
    NO_TOP_LEVEL_HELPERS = "FFT103"
    NO_IF_IN_TESTS = "FFT104"
    PRIVATE_CONSTANT_ORDER = "FFT105"
    NO_COMPLEX_COMPREHENSIONS = "FFT106"
    TEST_TYPES_DESCRIPTION = "FFT201"
    TEST_TYPES_EXPECTED_FIELD = "FFT202"
    LOCAL_TEST_TYPES_IMPORT = "FFT203"
    LOCAL_TEST_TYPES_FILE = "FFT204"
    TEST_FILE_NAME = "FFT301"
    TEST_FUNCTION_NAME = "FFT302"
    DATACLASS_PARAMETRIZE = "FFT401"
    ACCEPTS_TEST_CASE = "FFT402"
    TEST_CASE_ANNOTATION = "FFT403"
    EXPECTED_FIELD_ASSERTION = "FFT404"
    PARAMETRIZE_ARGUMENTS = "FFT405"
    PARAMETRIZE_TEST_CASE = "FFT406"
    PARAMETRIZE_IDS = "FFT407"
    INLINE_PARAMETRIZE_VALUES = "FFT408"
    NONEMPTY_PARAMETRIZE_VALUES = "FFT411"
    NO_DICT_TEST_CASES = "FFT412"
    LOCAL_TEST_CASE_CONSTRUCTORS = "FFT413"
    DESCRIPTION_LAMBDA_IDS = "FFT414"


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
