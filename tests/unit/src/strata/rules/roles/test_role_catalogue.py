"""Tests for the roles rule catalogue."""

from __future__ import annotations

import pytest

from strata.rules.authoring.models import RuleSpec
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
            expected_sfr204_message="runtime package directories must identify an owner",
            expected_sfr306_symbolic_name="TOP_LEVEL_DOMAIN_SHAPE",
            expected_sfr306_slug="top-level-domain-shape",
            expected_sfr306_message=(
                "top-level domains must be either role leaves or subdomain branches"
            ),
            expected_sfr306_remediation=(
                "Keep direct role content in a leaf domain, or move it into a named subdomain "
                "when the domain contains subdomains."
            ),
            expected_sfr307_message="top-level domains must not contain ad hoc direct modules",
            expected_sfr307_remediation=(
                "Move the module under a direct role boundary or into an owning named subdomain."
            ),
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
    assert "SFR206" not in codes
    assert RoleCode("SFR306").name == test_case.expected_sfr306_symbolic_name
    rules_by_code: dict[str, RuleSpec] = {rule.code: rule for rule in SFR_RULES}
    assert rules_by_code["SFR204"].message == test_case.expected_sfr204_message
    assert rules_by_code["SFR306"].slug == test_case.expected_sfr306_slug
    assert rules_by_code["SFR306"].message == test_case.expected_sfr306_message
    assert rules_by_code["SFR306"].remediation == test_case.expected_sfr306_remediation
    assert rules_by_code["SFR307"].message == test_case.expected_sfr307_message
    assert rules_by_code["SFR307"].remediation == test_case.expected_sfr307_remediation
