"""Fixed numeric cardinalities for test rules."""

from __future__ import annotations

from fensu.rules.authoring.models import RuleLimit
from fensu.rules.tests.types import FftCode


def get_test_rule_limits(code: FftCode) -> tuple[RuleLimit, ...]:
    """Return fixed limits owned by one test rule."""

    consuming_codes: frozenset[FftCode] = frozenset(
        {
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
    if code not in consuming_codes:
        return ()
    return (
        RuleLimit(
            name="minimum_parametrize_arguments",
            description="Minimum pytest parametrize positional arguments",
            value=2,
        ),
    )
