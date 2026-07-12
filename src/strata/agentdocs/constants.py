"""Agent skill generation and installation constants."""

from __future__ import annotations

from strata.rules.roles.types import RoleCode
from strata.rules.shape.types import ShapeCode
from strata.rules.tests.types import SftCode

GENERATED_MARKER: str = "<!-- generated-by: strata skills update -->"
SKILL_NAME: str = "strata"

RUNTIME_BASIC_CODES: frozenset[str] = frozenset(
    {RoleCode.TOP_LEVEL_DOMAIN_SHAPE, RoleCode.TOP_LEVEL_DIRECT_MODULES}
)
RUNTIME_NESTED_CODES: frozenset[str] = frozenset(
    {RoleCode.NESTED_DIRECT_MODULES, RoleCode.NESTED_DIRECT_SUBPACKAGES}
)
RUNTIME_PACKAGE_NAMING_CODES: frozenset[str] = frozenset({RoleCode.BANNED_GENERIC_PACKAGE_NAME})
RUNTIME_MAIN_CODES: frozenset[str] = frozenset(
    {RoleCode.MAIN_PACKAGE_LAYOUT, RoleCode.ENTRY_MODULE_SHAPE}
)
RUNTIME_HELPERS_CODES: frozenset[str] = frozenset(
    {
        RoleCode.HELPERS_MODULE_NAME,
        RoleCode.HELPERS_PACKAGE_LAYOUT,
        RoleCode.HELPERS_PACKAGE_SHAPE,
    }
)
RUNTIME_CLASSES_CODES: frozenset[str] = frozenset(
    {RoleCode.CLASSES_MODULE_NAME, RoleCode.CLASSES_ONE_CLASS_PER_MODULE}
)
RUNTIME_MODELS_CODES: frozenset[str] = frozenset(
    {RoleCode.MODELS_ONLY_MODELS, RoleCode.MODEL_DECLARATION_OUTSIDE_MODELS}
)
RUNTIME_TYPES_CODES: frozenset[str] = frozenset(
    {RoleCode.TYPES_ONLY_TYPES, RoleCode.TYPE_DECLARATION_OUTSIDE_TYPES}
)
RUNTIME_CONSTANTS_CODES: frozenset[str] = frozenset(
    {RoleCode.CONSTANTS_ONLY_CONSTANTS, RoleCode.CONSTANT_OUTSIDE_CONSTANTS}
)
RUNTIME_EXCEPTIONS_CODES: frozenset[str] = frozenset(
    {RoleCode.EXCEPTIONS_ONLY_EXCEPTIONS, RoleCode.EXCEPTION_DECLARATION_OUTSIDE_EXCEPTIONS}
)
RUNTIME_FROZEN_MODEL_CODES: frozenset[str] = frozenset({ShapeCode.MUTABLE_RESULT_MODEL})
RUNTIME_HELPERS_CONTENT_CODES: frozenset[str] = frozenset(
    {RoleCode.HELPERS_CLASSES_FILE_PRIVATE, RoleCode.PRIVATE_DEFINITION_ORDERING}
)
RUNTIME_ENTRY_CODES: frozenset[str] = frozenset({RoleCode.ENTRY_MODULE_SHAPE})

TEST_BASIC_CODES: frozenset[str] = frozenset(
    {SftCode.TEST_LAYOUT, SftCode.TEST_SCOPE, SftCode.TEST_MIRRORED_ROOT}
)
TEST_RUNTIME_MIRROR_CODES: frozenset[str] = frozenset(
    {SftCode.SRC_MIRROR_DEPTH, SftCode.SRC_PACKAGE_EXISTS, SftCode.SRC_AREA_EXISTS}
)
TEST_TOOLING_MIRROR_CODES: frozenset[str] = frozenset(
    {SftCode.SCRIPTS_MIRROR_DEPTH, SftCode.SCRIPTS_AREA_EXISTS}
)
TEST_CASE_FILE_CODES: frozenset[str] = frozenset(
    {SftCode.TEST_FILE_NAME, SftCode.LOCAL_TEST_TYPES_FILE}
)
TEST_AUTHORING_CODES: frozenset[str] = frozenset(
    {
        SftCode.TEST_TYPES_DESCRIPTION,
        SftCode.TEST_TYPES_EXPECTED_FIELD,
        SftCode.LOCAL_TEST_TYPES_IMPORT,
        SftCode.TEST_FUNCTION_NAME,
        SftCode.DATACLASS_PARAMETRIZE,
        SftCode.ACCEPTS_TEST_CASE,
        SftCode.TEST_CASE_ANNOTATION,
        SftCode.EXPECTED_FIELD_ASSERTION,
        SftCode.PARAMETRIZE_ARGUMENTS,
        SftCode.PARAMETRIZE_TEST_CASE,
        SftCode.PARAMETRIZE_IDS,
        SftCode.INLINE_PARAMETRIZE_VALUES,
        SftCode.NONEMPTY_PARAMETRIZE_VALUES,
        SftCode.NO_DICT_TEST_CASES,
        SftCode.LOCAL_TEST_CASE_CONSTRUCTORS,
        SftCode.DESCRIPTION_LAMBDA_IDS,
        SftCode.LOCAL_TEST_TYPES_FILE,
        SftCode.TEST_FILE_NAME,
    }
)

TOOLING_ADAPTER_CODES: frozenset[str] = frozenset(
    {
        RoleCode.TOOLING_ENTRYPOINT_SHAPE,
        RoleCode.TOOLING_ENTRYPOINT_DELEGATION,
        RoleCode.TOOLING_ENTRYPOINT_LINE_COUNT,
    }
)
TOOLING_PACKAGE_CODES: frozenset[str] = frozenset({RoleCode.TOOLING_PACKAGE_LAYOUT})
TOOLING_RULES_CODES: frozenset[str] = frozenset({RoleCode.RULES_ROLE_CONTENT})
