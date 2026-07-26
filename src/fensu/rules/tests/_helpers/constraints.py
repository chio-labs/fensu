"""Fixed exhaustive value sets for test rules."""

from __future__ import annotations

from fensu.rules.authoring.models import RuleConstraint
from fensu.rules.tests.types import FftCode


def get_test_rule_constraints(code: FftCode) -> tuple[RuleConstraint, ...]:
    """Return fixed constraints owned by one test rule."""

    if code is not FftCode.TEST_FILE_NAME:
        return ()
    return (
        RuleConstraint(
            name="excluded_test_support_filenames",
            description="Test support filenames excluded from test-module rules",
            values=(
                "__init__.py",
                "conftest.py",
                "helpers.py",
                "_test_helpers.py",
                "_test_types.py",
            ),
        ),
    )
