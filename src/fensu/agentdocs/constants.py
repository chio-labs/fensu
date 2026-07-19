"""Agent skill generation and installation constants."""

from __future__ import annotations

from fensu.rules.authoring.types import Threshold
from fensu.rules.roles.types import RoleCode
from fensu.rules.shape.types import ShapeCode
from fensu.rules.tests.types import FftCode

GENERATED_MARKER: str = "<!-- generated-by: fensu skills -->"
LEGACY_GENERATED_MARKER: str = "<!-- generated-by: fensu skills update -->"
GENERIC_SKILL_NAME: str = "fensu"
OWNERSHIP_MARKER_PREFIX: str = "<!-- fensu-skill-owner: "
OWNERSHIP_MARKER_SCHEMA: int = 1
PROJECT_SKILL_MARKER: str = "<!-- synchronized-project-skill-by: fensu skills -->"
PROJECT_SKILLS_RELATIVE_PATH: str = ".ai/knowledge/repo/skills"
SKILL_INPUT_FINGERPRINT_SCHEMA: int = 1
SKILL_NAME_PREFIX: str = "fensu-"
WINDOWS_RESERVED_SKILL_NAMES: frozenset[str] = frozenset({"con", "prn", "aux", "nul"})

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
        RoleCode.HELPERS_RESERVED_ROLE_FILENAMES,
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
    {FftCode.TEST_LAYOUT, FftCode.TEST_SCOPE, FftCode.TEST_MIRRORED_ROOT}
)
TEST_RUNTIME_MIRROR_CODES: frozenset[str] = frozenset(
    {FftCode.SRC_MIRROR_DEPTH, FftCode.SRC_PACKAGE_EXISTS, FftCode.SRC_AREA_EXISTS}
)
TEST_TOOLING_MIRROR_CODES: frozenset[str] = frozenset(
    {FftCode.SCRIPTS_MIRROR_DEPTH, FftCode.SCRIPTS_AREA_EXISTS}
)
TEST_CASE_FILE_CODES: frozenset[str] = frozenset(
    {FftCode.TEST_FILE_NAME, FftCode.LOCAL_TEST_TYPES_FILE}
)
TEST_AUTHORING_CODES: frozenset[str] = frozenset(
    {
        FftCode.TEST_TYPES_DESCRIPTION,
        FftCode.TEST_TYPES_EXPECTED_FIELD,
        FftCode.LOCAL_TEST_TYPES_IMPORT,
        FftCode.TEST_FUNCTION_NAME,
        FftCode.DATACLASS_PARAMETRIZE,
        FftCode.ACCEPTS_TEST_CASE,
        FftCode.TEST_CASE_ANNOTATION,
        FftCode.EXPECTED_FIELD_ASSERTION,
        FftCode.PARAMETRIZE_ARGUMENTS,
        FftCode.PARAMETRIZE_TEST_CASE,
        FftCode.PARAMETRIZE_IDS,
        FftCode.INLINE_PARAMETRIZE_VALUES,
        FftCode.NONEMPTY_PARAMETRIZE_VALUES,
        FftCode.NO_DICT_TEST_CASES,
        FftCode.LOCAL_TEST_CASE_CONSTRUCTORS,
        FftCode.DESCRIPTION_LAMBDA_IDS,
        FftCode.LOCAL_TEST_TYPES_FILE,
        FftCode.TEST_FILE_NAME,
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

THRESHOLD_RULE_CODES: dict[Threshold, frozenset[str]] = {
    Threshold.MAX_STATEMENTS: frozenset({ShapeCode.TOO_MANY_STATEMENTS}),
    Threshold.MAX_DISTINCT_CALLS: frozenset({ShapeCode.TOO_MANY_DISTINCT_CALLS}),
    Threshold.MAX_LOCALS: frozenset({ShapeCode.TOO_MANY_LOCALS}),
    Threshold.MAX_FILE_LINES: frozenset({RoleCode.SOURCE_FILE_LINE_COUNT}),
    Threshold.MAX_HELPERS_CONTAINER_MODULES: frozenset({RoleCode.HELPERS_PACKAGE_LAYOUT}),
    Threshold.MAX_MAIN_CONTAINER_MODULES: frozenset({RoleCode.MAIN_PACKAGE_LAYOUT}),
    Threshold.MAX_ROLE_DEPTH: frozenset(
        {RoleCode.HELPERS_PACKAGE_LAYOUT, RoleCode.MAIN_PACKAGE_LAYOUT}
    ),
    Threshold.MAX_POSITIONAL_ARGS: frozenset({ShapeCode.KEYWORD_ONLY_ARGUMENTS}),
    Threshold.MAX_ARGUMENTS: frozenset({ShapeCode.MAX_ARGUMENTS}),
    Threshold.MAX_STATEMENTS_GLOBAL: frozenset({ShapeCode.MAX_STATEMENTS_GLOBAL}),
    Threshold.MAX_SCRIPT_ENTRYPOINT_LINES: frozenset({RoleCode.TOOLING_ENTRYPOINT_LINE_COUNT}),
    Threshold.MIN_SHARED_DOMAIN_PREFIX_PACKAGES: frozenset({RoleCode.SHARED_DOMAIN_PREFIX}),
    Threshold.MIN_CUSTOM_RULE_TEST_CASES: frozenset({RoleCode.CUSTOM_RULE_TEST_COVERAGE}),
}
