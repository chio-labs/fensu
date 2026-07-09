"""Tests for the tests rule catalogue."""

from __future__ import annotations

import pytest

from strata.rules.tests.constants import SFT_RULES
from strata.rules.tests.types import SftCode
from tests.unit.src.strata.rules.tests._test_types import SftCatalogueTestCase


@pytest.mark.parametrize(
    "test_case",
    [
        SftCatalogueTestCase(
            description="tests rule catalogue matches tests code enum",
            expected_codes=tuple(code.value for code in SftCode),
            expected_unique_count=len(SftCode),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_tests_rule_catalogue_when_reading_codes_then_matches_tests_code_enum(
    test_case: SftCatalogueTestCase,
) -> None:
    codes: tuple[str, ...] = tuple(rule.code for rule in SFT_RULES)

    assert codes == test_case.expected_codes
    assert len(set(codes)) == test_case.expected_unique_count
