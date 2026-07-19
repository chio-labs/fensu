"""Tests for the hygiene rule catalogue."""

from __future__ import annotations

import pytest

from fensu.rules.hygiene.constants import FFH_RULES
from fensu.rules.hygiene.types import HygieneCode
from tests.unit.src.fensu.rules.hygiene._test_types import HygieneCatalogueTestCase


@pytest.mark.parametrize(
    "test_case",
    [
        HygieneCatalogueTestCase(
            description="hygiene rule catalogue matches hygiene code enum",
            expected_codes=tuple(code.value for code in HygieneCode),
            expected_unique_count=len(HygieneCode),
            expected_enabled_by_default=(True, True, True, True, True, True, True, True, True),
            expected_migrated_code="FFH009",
            expected_removed_code="FFR206",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_hygiene_rule_catalogue_when_reading_codes_then_matches_hygiene_code_enum(
    test_case: HygieneCatalogueTestCase,
) -> None:
    codes: tuple[str, ...] = tuple(rule.code for rule in FFH_RULES)

    assert codes == test_case.expected_codes
    assert len(set(codes)) == test_case.expected_unique_count
    assert tuple(rule.enabled_by_default for rule in FFH_RULES) == (
        test_case.expected_enabled_by_default
    )
    assert test_case.expected_migrated_code in codes
    assert test_case.expected_removed_code not in codes
