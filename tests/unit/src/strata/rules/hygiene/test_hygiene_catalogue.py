"""Tests for the hygiene rule catalogue."""

from __future__ import annotations

import pytest

from strata.rules.hygiene.constants import SFX_RULES
from strata.rules.hygiene.types import HygieneCode
from tests.unit.src.strata.rules.hygiene._test_types import HygieneCatalogueTestCase


@pytest.mark.parametrize(
    "test_case",
    [
        HygieneCatalogueTestCase(
            description="hygiene rule catalogue matches hygiene code enum",
            expected_codes=tuple(code.value for code in HygieneCode),
            expected_unique_count=len(HygieneCode),
            expected_enabled_by_default=(True, True, True, True, True, True, False, False),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_hygiene_rule_catalogue_when_reading_codes_then_matches_hygiene_code_enum(
    test_case: HygieneCatalogueTestCase,
) -> None:
    codes: tuple[str, ...] = tuple(rule.code for rule in SFX_RULES)

    assert codes == test_case.expected_codes
    assert len(set(codes)) == test_case.expected_unique_count
    assert tuple(rule.enabled_by_default for rule in SFX_RULES) == (
        test_case.expected_enabled_by_default
    )
