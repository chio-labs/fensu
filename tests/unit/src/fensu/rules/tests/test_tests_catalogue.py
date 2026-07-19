"""Tests for the tests rule catalogue."""

from __future__ import annotations

import pytest

from fensu.rules.authoring.models import RuleSpec
from fensu.rules.tests.constants import FFT_RULES
from fensu.rules.tests.types import FftCode
from tests.unit.src.fensu.rules.tests._test_types import FftCatalogueTestCase, FftGuidanceTestCase


@pytest.mark.parametrize(
    "test_case",
    [
        FftCatalogueTestCase(
            description="tests rule catalogue preserves semantic numbering bands",
            expected_codes=(
                "FFT001",
                "FFT002",
                "FFT003",
                "FFT004",
                "FFT005",
                "FFT006",
                "FFT007",
                "FFT008",
                "FFT101",
                "FFT102",
                "FFT103",
                "FFT104",
                "FFT105",
                "FFT106",
                "FFT201",
                "FFT202",
                "FFT203",
                "FFT204",
                "FFT301",
                "FFT302",
                "FFT401",
                "FFT402",
                "FFT403",
                "FFT404",
                "FFT405",
                "FFT406",
                "FFT407",
                "FFT408",
                "FFT411",
                "FFT412",
                "FFT413",
                "FFT414",
            ),
            expected_unique_count=len(FftCode),
            expected_removed_codes=("FFT409", "FFT410"),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_tests_rule_catalogue_when_reading_codes_then_matches_tests_code_enum(
    test_case: FftCatalogueTestCase,
) -> None:
    codes: tuple[str, ...] = tuple(rule.code for rule in FFT_RULES)

    assert codes == test_case.expected_codes
    assert len(set(codes)) == test_case.expected_unique_count
    assert all(code not in codes for code in test_case.expected_removed_codes)


@pytest.mark.parametrize(
    "test_case",
    [
        FftGuidanceTestCase(
            description="inline parametrize guidance requires visibly local values",
            rule_code=FftCode.INLINE_PARAMETRIZE_VALUES,
            expected_message=(
                "pytest parametrize values must be a visible list, tuple, or local comprehension"
            ),
            expected_remediation=(
                "Inline the case sequence in @pytest.mark.parametrize so its cases are visible "
                "beside the test."
            ),
        ),
        FftGuidanceTestCase(
            description="conditional test guidance distinguishes parametrization from splitting",
            rule_code=FftCode.NO_IF_IN_TESTS,
            expected_message=(
                "tests and local test helpers must not contain conditional control flow"
            ),
            expected_remediation=(
                "Use parametrized cases when setup and assertions remain branch-free; otherwise "
                "split the behavior into separate test functions. Keep local test helpers "
                "deterministic with per-variant functions or dataclass-driven case data."
            ),
        ),
        FftGuidanceTestCase(
            description="complex comprehension guidance recommends a named transformation",
            rule_code=FftCode.NO_COMPLEX_COMPREHENSIONS,
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
    test_case: FftGuidanceTestCase,
) -> None:
    rules_by_code: dict[str, RuleSpec] = {rule.code: rule for rule in FFT_RULES}
    rule: RuleSpec = rules_by_code[test_case.rule_code]

    assert rule.message == test_case.expected_message
    assert rule.remediation == test_case.expected_remediation
