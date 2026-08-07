"""Fixed exhaustive value sets for test rules."""

from __future__ import annotations

from fensu.rules.authoring.models import RuleConstraint
from fensu.rules.tests.types import FftCode


def get_test_rule_constraints(code: FftCode) -> tuple[RuleConstraint, ...]:
    """Return fixed constraints owned by one test rule."""

    test_module_codes: frozenset[FftCode] = frozenset(
        {
            FftCode.NO_TOP_LEVEL_HELPERS,
            FftCode.PRIVATE_CONSTANT_ORDER,
            FftCode.LOCAL_TEST_TYPES_IMPORT,
            FftCode.LOCAL_TEST_TYPES_FILE,
            FftCode.TEST_FILE_NAME,
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
        }
    )
    if code in test_module_codes:
        return (_excluded_test_support_filenames(include_helpers=True),)
    if code is FftCode.NO_IF_IN_TESTS:
        return (
            _excluded_test_support_filenames(include_helpers=False),
            RuleConstraint(
                name="helper_module_filenames",
                description="Test helper filenames included in conditional-flow enforcement",
                values=("helpers.py", "_test_helpers.py"),
            ),
        )
    if code is FftCode.SCENARIO_MODELS_DATACLASSES:
        return (
            RuleConstraint(
                name="scenario_model_filenames",
                description="Scenario model filenames requiring dataclass-only declarations",
                values=("scenario_models.py",),
            ),
        )
    return ()


def _excluded_test_support_filenames(*, include_helpers: bool) -> RuleConstraint:
    values: tuple[str, ...] = ("__init__.py", "conftest.py", "_test_types.py")
    if include_helpers:
        values = (*values, "helpers.py", "_test_helpers.py")
    return RuleConstraint(
        name="excluded_test_support_filenames",
        description="Test support filenames excluded from this test-module rule",
        values=values,
    )
