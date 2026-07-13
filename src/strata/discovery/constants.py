"""Discovery constants for role-position facts and scope routing."""

from __future__ import annotations

from strata.config.constants import DEFAULT_ROLE_FILE_NAMES
from strata.discovery.types import RoleName
from strata.rules.authoring.types import Family

ROLE_FILE_TO_NAME: dict[str, str] = {
    file_name: file_name.removesuffix(".py") for file_name in DEFAULT_ROLE_FILE_NAMES
}
HELPERS_DIRECTORY_NAME: str = "_helpers"
LEGACY_HELPERS_DIRECTORY_NAME: str = "helpers"
ROLE_DIRECTORY_TO_NAME: dict[str, RoleName] = {
    RoleName.MAIN: RoleName.MAIN,
    HELPERS_DIRECTORY_NAME: RoleName.HELPERS,
    RoleName.CLASSES: RoleName.CLASSES,
}
ROLE_DIR_NAMES: frozenset[str] = frozenset(ROLE_DIRECTORY_TO_NAME)
STRUCTURAL_MODULE_PART_TO_NAME: dict[str, RoleName] = {
    **ROLE_DIRECTORY_TO_NAME,
    RoleName.MODELS: RoleName.MODELS,
    RoleName.TYPES: RoleName.TYPES,
    RoleName.CONSTANTS: RoleName.CONSTANTS,
    RoleName.EXCEPTIONS: RoleName.EXCEPTIONS,
}
INIT_MODULE_FILE_NAME: str = "__init__.py"
INIT_MODULE_NAME: str = "__init__"
MAIN_MODULE_FILE_NAME: str = "main.py"
MINIMUM_NESTED_PATH_PARTS: int = 2
PYTHON_FILE_SUFFIX: str = ".py"

ROOT_FAMILIES: frozenset[Family] = frozenset(
    {
        Family.LAYERS,
        Family.ROLES,
        Family.SHAPE,
        Family.NAMING,
        Family.HYGIENE,
        Family.ANNOTATIONS,
    }
)
TEST_FAMILIES: frozenset[Family] = frozenset({Family.ANNOTATIONS, Family.TESTS})
TOOLING_FAMILIES: frozenset[Family] = ROOT_FAMILIES
