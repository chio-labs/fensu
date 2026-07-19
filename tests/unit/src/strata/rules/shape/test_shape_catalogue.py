"""Tests for the shape rule catalogue."""

from __future__ import annotations

import pytest

from strata.rules.authoring.models import RuleSpec
from strata.rules.shape.constants import SFS_RULES
from strata.rules.shape.types import ShapeCode
from tests.unit.src.strata.rules.shape._test_types import (
    ShapeCatalogueTestCase,
    ShapeDefaultOffTestCase,
    ShapeGuidanceTestCase,
)
from tests.unit.src.strata.rules.shape.helpers import shape_rule_by_code


@pytest.mark.parametrize(
    "test_case",
    [
        ShapeCatalogueTestCase(
            description="shape rule catalogue matches shape code enum",
            expected_codes=tuple(code.value for code in ShapeCode),
            expected_unique_count=len(ShapeCode),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_shape_rule_catalogue_when_reading_codes_then_matches_shape_code_enum(
    test_case: ShapeCatalogueTestCase,
) -> None:
    codes: tuple[str, ...] = tuple(rule.code for rule in SFS_RULES)

    assert codes == test_case.expected_codes
    assert len(set(codes)) == test_case.expected_unique_count


@pytest.mark.parametrize(
    "test_case",
    [
        ShapeDefaultOffTestCase(
            description="parameter mutation in phase helpers is default off",
            rule_code=ShapeCode.PARAMETER_MUTATION_IN_PHASE_HELPERS,
            expected_enabled_by_default=False,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_shape_rule_catalogue_when_reading_sfs102_then_rule_is_default_off(
    test_case: ShapeDefaultOffTestCase,
) -> None:
    rule: RuleSpec = shape_rule_by_code(rule_code=test_case.rule_code)

    assert rule.enabled_by_default is test_case.expected_enabled_by_default


@pytest.mark.parametrize(
    "test_case",
    [
        ShapeGuidanceTestCase(
            description="complex comprehension guidance recommends a named transformation",
            rule_code=ShapeCode.NO_COMPLEX_COMPREHENSIONS,
            expected_message=(
                "nested or multi-generator comprehensions hide control flow and data shapes"
            ),
            expected_remediation=(
                "Extract a named helper when the transformation has a coherent purpose. For "
                "one-off local logic, use simple statements with named intermediate values "
                "instead of nested comprehension control flow."
            ),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_complex_comprehension_rule_when_reading_guidance_then_explains_clear_fix(
    test_case: ShapeGuidanceTestCase,
) -> None:
    rule: RuleSpec = shape_rule_by_code(rule_code=test_case.rule_code)

    assert rule.message == test_case.expected_message
    assert rule.remediation == test_case.expected_remediation
