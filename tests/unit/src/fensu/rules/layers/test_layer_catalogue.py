"""Tests for the layer rule catalogue."""

from __future__ import annotations

import pytest

from fensu.rules.layers.constants import FFL_RULES
from fensu.rules.layers.types import LayerCode
from tests.unit.src.fensu.rules.layers._test_types import LayerCatalogueTestCase


@pytest.mark.parametrize(
    "test_case",
    [
        LayerCatalogueTestCase(
            description="layer rule catalogue matches layer code enum",
            expected_codes=tuple(code.value for code in LayerCode),
            expected_unique_count=len(LayerCode),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_layer_rule_catalogue_when_reading_codes_then_matches_layer_code_enum(
    test_case: LayerCatalogueTestCase,
) -> None:
    codes: tuple[str, ...] = tuple(rule.code for rule in FFL_RULES)

    assert codes == test_case.expected_codes
    assert len(set(codes)) == test_case.expected_unique_count
