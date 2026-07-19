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
            description="tests rule catalogue preserves semantic numbering bands",
            expected_codes=(
                "SFT001",
                "SFT002",
                "SFT003",
                "SFT004",
                "SFT005",
                "SFT006",
                "SFT007",
                "SFT008",
                "SFT101",
                "SFT102",
                "SFT103",
                "SFT104",
                "SFT105",
                "SFT106",
                "SFT201",
                "SFT202",
                "SFT203",
                "SFT204",
                "SFT301",
                "SFT302",
                "SFT401",
                "SFT402",
                "SFT403",
                "SFT404",
                "SFT405",
                "SFT406",
                "SFT407",
                "SFT408",
                "SFT411",
                "SFT412",
                "SFT413",
                "SFT414",
            ),
            expected_unique_count=len(SftCode),
            expected_removed_codes=("SFT409", "SFT410"),
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
    assert all(code not in codes for code in test_case.expected_removed_codes)


@pytest.mark.parametrize(
    "test_case",
    [
        SftGuidanceTestCase(
            description="inline parametrize guidance requires visibly local values",
            rule_code=SftCode.INLINE_PARAMETRIZE_VALUES,
            expected_message=(
                "pytest parametrize values must be a visible list, tuple, or local comprehension"
            ),
            expected_remediation=(
                "Inline the case sequence in @pytest.mark.parametrize so its cases are visible "
                "beside the test."
            ),
        ),
        SftGuidanceTestCase(
            description="conditional test guidance distinguishes parametrization from splitting",
            rule_code=SftCode.NO_IF_IN_TESTS,
            expected_message=(
                "tests and local test helpers must not contain conditional control flow"
            ),
            expected_remediation=(
                "Use parametrized cases when setup and assertions remain branch-free; otherwise "
                "split the behavior into separate test functions. Keep local test helpers "
                "deterministic with per-variant functions or dataclass-driven case data."
            ),
        ),
        SftGuidanceTestCase(
            description="complex comprehension guidance recommends a named transformation",
            rule_code=SftCode.NO_COMPLEX_COMPREHENSIONS,
            expected_message=(
                "nested or multi-generator comprehensions hide control flow and data shapes"
            ),
            expected_remediation=(
                "Extract a named helper when the transformation has a coherent purpose. For "
                "one-off local logic, use simple statements with named intermediate values "
                "instead of nested comprehension control flow."
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
