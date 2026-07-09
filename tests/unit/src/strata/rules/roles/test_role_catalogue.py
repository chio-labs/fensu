"""Tests for the roles rule catalogue."""

from __future__ import annotations

import pytest

from strata.rules.roles.constants import SFR_RULES
from strata.rules.roles.types import RoleCode
from tests.unit.src.strata.rules.roles._test_types import SfrCatalogueTestCase


@pytest.mark.parametrize(
    "test_case",
    [
        SfrCatalogueTestCase(
            description="roles rule catalogue matches implemented role codes",
            expected_codes=tuple(code.value for code in RoleCode),
            expected_unique_count=len(RoleCode),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_roles_rule_catalogue_when_reading_codes_then_matches_role_code_enum(
    test_case: SfrCatalogueTestCase,
) -> None:
    codes: tuple[str, ...] = tuple(rule.code for rule in SFR_RULES)

    assert codes == test_case.expected_codes
    assert len(set(codes)) == test_case.expected_unique_count
