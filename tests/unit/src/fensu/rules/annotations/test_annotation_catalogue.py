"""Tests for the annotation rule catalogue."""

from __future__ import annotations

import pytest

from fensu.rules.annotations.constants import FFA_RULES
from fensu.rules.annotations.types import AnnotationCode
from tests.unit.src.fensu.rules.annotations._test_types import AnnotationCatalogueTestCase


@pytest.mark.parametrize(
    "test_case",
    [
        AnnotationCatalogueTestCase(
            description="annotation rule catalogue matches annotation code enum",
            expected_codes=tuple(code.value for code in AnnotationCode),
            expected_unique_count=len(AnnotationCode),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_annotation_rule_catalogue_when_reading_codes_then_matches_annotation_code_enum(
    test_case: AnnotationCatalogueTestCase,
) -> None:
    codes: tuple[str, ...] = tuple(rule.code for rule in FFA_RULES)

    assert codes == test_case.expected_codes
    assert len(set(codes)) == test_case.expected_unique_count
