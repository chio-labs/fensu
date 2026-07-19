"""Type-layer vocabulary shared by public custom test-rule equivalents."""

from enum import StrEnum
from typing import NamedTuple

type LayoutIssue = tuple[str, str]


class ImportOwnership(NamedTuple):
    """Structural ownership facts for one imported module path."""

    package: str | None
    owner: tuple[str, ...]
    domain: str | None
    role: str | None
    tail: tuple[str, ...]


class ExemplarLayerPathName(StrEnum):
    """Path names used for local layer-policy routing."""

    INIT = "__init__.py"
    RULES = "rules"
    EXEMPLARS = "exemplars"


class ExemplarRoleName(StrEnum):
    """Structural role names used by ownership exemplars."""

    MAIN = "main"
    HELPERS = "_helpers"


class ExemplarBannedPackageName(StrEnum):
    """Generic package names rejected by ownership policy."""

    BASE = "base"
    COMMON = "common"
    HELPERS = "helpers"
    LIB = "lib"
    MISC = "misc"
    SHARED = "shared"
    UTIL = "util"
    UTILS = "utils"


class ExemplarToolingRoleName(StrEnum):
    """Approved tooling package role directories."""

    MAIN = "main"
    HELPERS = "_helpers"
    CLASSES = "classes"
    RULES = "rules"


class ExemplarToolingRoleFile(StrEnum):
    """Approved tooling package role files."""

    MODELS = "models.py"
    TYPES = "types.py"
    CONSTANTS = "constants.py"
    EXCEPTIONS = "exceptions.py"


class ExemplarTestScopeName(StrEnum):
    """Supported test scope directory names."""

    UNIT = "unit"
    INTEGRATION = "integration"
    E2E = "e2e"


class ExemplarTestAreaName(StrEnum):
    """Special configured runtime test areas."""

    ROOT = "__root__"


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
    MINIMUM_PATH_PARTS = "2"
