"""Tests for the tests rule catalogue."""

from __future__ import annotations

import pytest

from strata.rules.authoring.models import RuleSpec
from strata.rules.tests.constants import SFT_RULES
from strata.rules.tests.types import SftCode
from tests.unit.src.strata.rules.tests._test_types import SftCatalogueTestCase, SftGuidanceTestCase


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


@pytest.mark.parametrize(
    "test_case",
    [
        SftGuidanceTestCase(
            description="conditional test guidance recommends cases and local helpers",
            rule_code=SftCode.NO_IF_IN_TESTS,
            expected_message="test bodies must not contain conditional control flow",
            expected_remediation=(
                "Split behavioral branches into parametrized cases and move conditional setup "
                "or selection into local test helpers."
            ),
        ),
        SftGuidanceTestCase(
            description="complex comprehension guidance recommends ordinary staged code",
            rule_code=SftCode.NO_COMPLEX_COMPREHENSIONS,
            expected_message=(
                "nested or multi-generator comprehensions hide control flow and data shapes"
            ),
            expected_remediation=(
                "Rewrite this as ordinary statements with named intermediate values. Use "
                "explicit loops when needed, and extract a helper only when the transformation "
                "is a distinct operation."
            ),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_readability_rules_when_reading_guidance_then_explains_clear_fix(
    test_case: SftGuidanceTestCase,
) -> None:
    rules_by_code: dict[str, RuleSpec] = {rule.code: rule for rule in SFT_RULES}
    rule: RuleSpec = rules_by_code[test_case.rule_code]

    assert rule.message == test_case.expected_message
    assert rule.remediation == test_case.expected_remediation
