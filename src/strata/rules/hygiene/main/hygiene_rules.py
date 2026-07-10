"""Hygiene rule catalogue entries."""

from __future__ import annotations

from strata.rules.authoring.models import RuleSpec
from strata.rules.authoring.types import Family
from strata.rules.hygiene.helpers.checks import (
    no_assert_in_runtime,
    no_complex_comprehensions_in_tooling,
    no_magic_numeric_comparisons,
    no_raw_builtin_raise,
    no_standalone_comments,
    no_swallowed_exception_probe,
    no_unnamed_string_decisions,
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
            remediation=(
                "Keep one concise summary line and move extended rationale into documentation "
                "or tests."
            ),
            check=single_line_docstrings,
        ),
        RuleSpec(
            code=HygieneCode.NO_STANDALONE_COMMENTS,
            family=Family.HYGIENE,
            slug="no-standalone-comments",
            message="standalone comments are not allowed; prefer clear names or docs/tests",
            remediation=(
                "Replace the comment with clearer names or move lasting explanation into "
                "documentation or tests."
            ),
            check=no_standalone_comments,
        ),
        RuleSpec(
            code=HygieneCode.NO_RAW_BUILTIN_RAISE,
            family=Family.HYGIENE,
            slug="no-raw-builtin-raise",
            message="runtime code must raise structured errors instead of raw built-in exceptions",
            remediation=(
                "Raise a domain-specific exception from exceptions.py with a stable actionable "
                "message."
            ),
            check=no_raw_builtin_raise,
        ),
        RuleSpec(
            code=HygieneCode.NO_ASSERT_IN_RUNTIME,
            family=Family.HYGIENE,
            slug="no-assert-in-runtime",
            message="runtime code must not use assert for invariants; raise a structured error",
            remediation=(
                "Replace assert with an explicit guard that raises a domain-specific exception."
            ),
            check=no_assert_in_runtime,
        ),
        RuleSpec(
            code=HygieneCode.NO_SWALLOWED_EXCEPTION_PROBE,
            family=Family.HYGIENE,
            slug="no-swallowed-exception-probe",
            message="runtime code must not swallow broad exceptions as existence probe answers",
            remediation=(
                "Use an explicit metadata or existence check, or catch only the expected "
                "exception and preserve failures."
            ),
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
        RuleSpec(
            code=HygieneCode.NO_UNNAMED_STRING_DECISIONS,
            family=Family.HYGIENE,
            slug="no-unnamed-string-decisions",
            message="string literals must not directly control comparison behavior",
            remediation=(
                "Name the decision value in constants.py or compare against an enum member so "
                "the branch expresses the concept it represents."
            ),
            check=no_unnamed_string_decisions,
        ),
        RuleSpec(
            code=HygieneCode.NO_MAGIC_NUMERIC_COMPARISONS,
            family=Family.HYGIENE,
            slug="no-magic-numeric-comparisons",
            message="non-canonical numeric literals must not directly control comparisons",
            remediation=(
                "Name the threshold or sentinel in constants.py and compare against that name; "
                "only -1, 0, and 1 are self-explanatory comparison values."
            ),
            check=no_magic_numeric_comparisons,
        ),
    )
