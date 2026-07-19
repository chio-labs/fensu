"""Tests for shared repository-relative path patterns."""

from __future__ import annotations

import pytest

from fensu.config._helpers.path_patterns import path_pattern_matches, path_pattern_specificity
from tests.unit.src.fensu.config._test_types import (
    PathPatternSpecificityTestCase,
    PathPatternTestCase,
)


@pytest.mark.parametrize(
    "test_case",
    [
        PathPatternTestCase(
            description="single star stays within one path component",
            pattern="src/*/main.py",
            path="src/pkg/main.py",
            expected_matches=True,
        ),
        PathPatternTestCase(
            description="single star does not cross path components",
            pattern="src/*/main.py",
            path="src/pkg/orders/main.py",
            expected_matches=False,
        ),
        PathPatternTestCase(
            description="double star crosses zero path components",
            pattern="src/**/main.py",
            path="src/main.py",
            expected_matches=True,
        ),
        PathPatternTestCase(
            description="double star crosses multiple path components",
            pattern="src/**/main.py",
            path="src/pkg/orders/main.py",
            expected_matches=True,
        ),
        PathPatternTestCase(
            description="slash pattern is anchored to repository root",
            pattern="src/**/*.py",
            path="nested/src/pkg/main.py",
            expected_matches=False,
        ),
        PathPatternTestCase(
            description="basename pattern matches at any repository depth",
            pattern="*.py",
            path="src/pkg/orders/main.py",
            expected_matches=True,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_path_pattern_when_matching_reported_path_then_applies_posix_glob_semantics(
    test_case: PathPatternTestCase,
) -> None:
    matches: bool = path_pattern_matches(pattern=test_case.pattern, path=test_case.path)

    assert matches is test_case.expected_matches


@pytest.mark.parametrize(
    "test_case",
    [
        PathPatternSpecificityTestCase(
            description="literal path has maximal positive evidence",
            pattern="src/pkg/main/read.py",
            expected_specificity=(4, 17, 0, 0),
        ),
        PathPatternSpecificityTestCase(
            description="globstar and wildcard lower specificity independently",
            pattern="src/**/main/*.py",
            expected_specificity=(2, 10, -1, -1),
        ),
        PathPatternSpecificityTestCase(
            description="multiple single wildcards lower final precedence component",
            pattern="src/*/main/read*.py",
            expected_specificity=(2, 14, 0, -2),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_normalized_pattern_when_scoring_then_returns_documented_specificity_tuple(
    test_case: PathPatternSpecificityTestCase,
) -> None:
    specificity: tuple[int, int, int, int] = path_pattern_specificity(test_case.pattern)

    assert specificity == test_case.expected_specificity
