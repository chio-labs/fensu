"""Actionable catalogue metadata for test-convention rules."""

from __future__ import annotations

from fensu.rules.tests.types import FftCode


def test_rule_details(code: FftCode) -> tuple[str, str]:
    """Return the contract and normal correction for one test rule."""

    details: dict[FftCode, tuple[str, str]] = {
        FftCode.INIT_MODULE_EMPTY: (
            "test package __init__.py files must be empty or docstring-only",
            "Remove runtime declarations from __init__.py and import them from their owning "
            "module.",
        ),
        FftCode.ABSOLUTE_IMPORTS: (
            "tests must use absolute imports",
            "Replace the relative import with the full tests or application package path.",
        ),
        FftCode.TEST_TYPES_DESCRIPTION: (
            "test-case dataclasses must define a description field",
            "Add description: str so parametrized cases explain the behavior they represent.",
        ),
        FftCode.TEST_TYPES_EXPECTED_FIELD: (
            "test-case dataclasses must define at least one expected_ field",
            "Name expected outcomes with an expected_ prefix and assert against them in the test.",
        ),
        FftCode.LOCAL_TEST_TYPES_IMPORT: (
            "tests must import test-case types from their local _test_types.py",
            "Move the dataclass beside the test and import it through the mirrored absolute path.",
        ),
        FftCode.TEST_FILE_NAME: (
            "test modules must use a test_ filename",
            "Rename the module to test_<behavior>.py.",
        ),
        FftCode.TEST_FUNCTION_NAME: (
            "test functions must use test_given_<state>_when_<action>_then_<outcome>",
            "Rename the test so its precondition, action, and expected behavior are explicit.",
        ),
        FftCode.DATACLASS_PARAMETRIZE: (
            "tests must use dataclass-backed pytest parameterization",
            "Add @pytest.mark.parametrize with local test_case dataclass instances.",
        ),
        FftCode.ACCEPTS_TEST_CASE: (
            "parametrized tests must accept a test_case argument",
            "Name the parameter test_case and read inputs and expectations from that object.",
        ),
        FftCode.TEST_CASE_ANNOTATION: (
            "test_case parameters must use a local test-case dataclass annotation",
            "Annotate test_case with a dataclass imported from the local _test_types.py.",
        ),
        FftCode.EXPECTED_FIELD_ASSERTION: (
            "tests must assert against an expected_ field from test_case",
            "Store the expected outcome on test_case and reference it in a behavior assertion.",
        ),
        FftCode.PARAMETRIZE_ARGUMENTS: (
            "pytest parametrize decorators must define parameter names and values",
            "Pass both the parameter-name string and the case sequence to parametrize.",
        ),
        FftCode.PARAMETRIZE_TEST_CASE: (
            "pytest parametrize must expose cases through the test_case parameter",
            'Use "test_case" as the parametrize parameter name.',
        ),
        FftCode.PARAMETRIZE_IDS: (
            "pytest parametrize decorators must define readable case ids",
            "Set ids to the case descriptions, normally with ids=lambda case: case.description.",
        ),
        FftCode.INLINE_PARAMETRIZE_VALUES: (
            "pytest parametrize values must be a visible list, tuple, or local comprehension",
            "Inline the case sequence in @pytest.mark.parametrize so its cases are visible beside "
            "the test.",
        ),
        FftCode.NONEMPTY_PARAMETRIZE_VALUES: (
            "pytest parametrize case sequences must not be empty",
            "Add at least one behavior case or remove the test until a real case exists.",
        ),
        FftCode.NO_DICT_TEST_CASES: (
            "pytest cases must use typed dataclasses instead of dictionaries",
            "Define a local frozen test-case dataclass and construct one instance per case.",
        ),
        FftCode.LOCAL_TEST_CASE_CONSTRUCTORS: (
            "pytest cases must construct dataclasses from the local _test_types.py",
            "Move or define the test-case dataclass locally and instantiate that type directly.",
        ),
        FftCode.DESCRIPTION_LAMBDA_IDS: (
            "pytest case ids must come from each test case description",
            "Use ids=lambda case: case.description so failures identify the behavior clearly.",
        ),
        FftCode.LOCAL_TEST_TYPES_FILE: (
            "test directories must provide a local _test_types.py",
            "Create _test_types.py beside the test module and place test-case dataclasses there.",
        ),
        FftCode.NO_TOP_LEVEL_HELPERS: (
            "test modules may contain only tests, imports, and declarations",
            "Move reusable functions into the local helpers.py module.",
        ),
        FftCode.TEST_LAYOUT: (
            "tests must live under a configured test root and supported scope",
            "Move the test beneath a configured test root and unit, integration, or e2e scope.",
        ),
        FftCode.TEST_SCOPE: (
            "test scope must be unit, integration, or e2e",
            "Move the test under tests/unit, tests/integration, or tests/e2e.",
        ),
        FftCode.TEST_MIRRORED_ROOT: (
            "test directories must mirror a configured runtime or tooling root",
            "Mirror the complete configured source or tooling path beneath the test scope.",
        ),
        FftCode.SRC_MIRROR_DEPTH: (
            "runtime tests must include an area beneath the configured source root",
            "Move the test beneath the package and source area it exercises.",
        ),
        FftCode.SRC_PACKAGE_EXISTS: (
            "runtime tests must mirror a configured source package",
            "Correct the mirrored package name or move the test to the package it exercises.",
        ),
        FftCode.SRC_AREA_EXISTS: (
            "runtime tests must mirror an existing source package area",
            "Correct the mirrored area path so it matches the runtime module location.",
        ),
        FftCode.SCRIPTS_MIRROR_DEPTH: (
            "tooling tests must include an area beneath the configured tooling root",
            "Move the test beneath the configured tooling area it exercises.",
        ),
        FftCode.SCRIPTS_AREA_EXISTS: (
            "tooling tests must mirror an existing configured tooling area",
            "Correct the mirrored area path so it matches the tooling location.",
        ),
        FftCode.NO_IF_IN_TESTS: (
            "tests and local test helpers must not contain conditional control flow",
            "Use parametrized cases when setup and assertions remain branch-free; otherwise "
            "split the behavior into separate test functions. Keep local test helpers "
            "deterministic with per-variant functions or dataclass-driven case data.",
        ),
        FftCode.PRIVATE_CONSTANT_ORDER: (
            "private test constants must appear before test functions",
            "Move the private constant above the first test so module setup is visible before "
            "behavior.",
        ),
        FftCode.NO_COMPLEX_COMPREHENSIONS: (
            "nested or multi-generator comprehensions hide control flow and data shapes",
            "Extract a named helper when the transformation has a coherent purpose. For one-off "
            "local logic, use simple statements with named intermediate values instead of nested "
            "comprehension control flow.",
        ),
    }
    return details[code]
