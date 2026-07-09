"""Tests for the naming rule catalogue."""

from __future__ import annotations

import pytest

from strata.rules.naming.constants import SFN_RULES
from strata.rules.naming.types import NamingCode
from tests.unit.src.strata.rules.naming._test_types import SfnCatalogueTestCase


@pytest.mark.parametrize(
    "test_case",
    [
        SfnCatalogueTestCase(
            description="naming rule catalogue matches naming code enum",
            expected_codes=tuple(code.value for code in NamingCode),
            expected_unique_count=len(NamingCode),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_naming_rule_catalogue_when_reading_codes_then_matches_naming_code_enum(
    test_case: SfnCatalogueTestCase,
) -> None:
    codes: tuple[str, ...] = tuple(rule.code for rule in SFN_RULES)

    assert codes == test_case.expected_codes
    assert len(set(codes)) == test_case.expected_unique_count
