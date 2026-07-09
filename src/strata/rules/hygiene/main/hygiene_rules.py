"""Hygiene rule catalogue entries."""

from __future__ import annotations

from strata.rules.authoring.models import RuleSpec
from strata.rules.authoring.types import Family
from strata.rules.hygiene.helpers.checks import (
    no_assert_in_runtime,
    no_complex_comprehensions_in_tooling,
    no_raw_builtin_raise,
    no_standalone_comments,
    no_swallowed_exception_probe,
    single_line_docstrings,
)
from strata.rules.hygiene.types import HygieneCode


def hygiene_rules() -> tuple[RuleSpec, ...]:
    """Build hygiene family rules."""

    return (
        RuleSpec(
            code=HygieneCode.SINGLE_LINE_DOCSTRINGS,
            family=Family.HYGIENE,
            slug="single-line-docstrings",
            message=(
                "docstrings must be a single line; move extended explanation into docs or tests"
            ),
            check=single_line_docstrings,
        ),
        RuleSpec(
            code=HygieneCode.NO_STANDALONE_COMMENTS,
            family=Family.HYGIENE,
            slug="no-standalone-comments",
            message="standalone comments are not allowed; prefer clear names or docs/tests",
            check=no_standalone_comments,
        ),
        RuleSpec(
            code=HygieneCode.NO_RAW_BUILTIN_RAISE,
            family=Family.HYGIENE,
            slug="no-raw-builtin-raise",
            message="runtime code must raise structured errors instead of raw built-in exceptions",
            check=no_raw_builtin_raise,
        ),
        RuleSpec(
            code=HygieneCode.NO_ASSERT_IN_RUNTIME,
            family=Family.HYGIENE,
            slug="no-assert-in-runtime",
            message="runtime code must not use assert for invariants; raise a structured error",
            check=no_assert_in_runtime,
        ),
        RuleSpec(
            code=HygieneCode.NO_SWALLOWED_EXCEPTION_PROBE,
            family=Family.HYGIENE,
            slug="no-swallowed-exception-probe",
            message="runtime code must not swallow broad exceptions as existence probe answers",
            check=no_swallowed_exception_probe,
        ),
        RuleSpec(
            code=HygieneCode.NO_COMPLEX_COMPREHENSIONS_IN_TOOLING,
            family=Family.HYGIENE,
            slug="no-complex-comprehensions-in-tooling",
            message="nested or multi-generator comprehensions hide control flow and data shapes",
            check=no_complex_comprehensions_in_tooling,
            remediation=(
                "Rewrite this as ordinary statements with named intermediate values. Use "
                "explicit loops when needed, and extract a helper only when the transformation "
                "is a distinct operation."
            ),
        ),
    )
