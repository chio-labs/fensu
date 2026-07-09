"""Tests for the shape rule catalogue."""

from __future__ import annotations

import pytest

from strata.rules.authoring.models import RuleSpec
from strata.rules.shape.constants import SFS_RULES
from strata.rules.shape.types import ShapeCode
from tests.unit.src.strata.rules.shape._test_types import (
    ShapeCatalogueTestCase,
    ShapeDefaultOffTestCase,
)


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
    rule: RuleSpec = next(rule for rule in SFS_RULES if rule.code == test_case.rule_code)

    assert rule.enabled_by_default is test_case.expected_enabled_by_default
