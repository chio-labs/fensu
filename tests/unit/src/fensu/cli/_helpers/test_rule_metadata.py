"""Tests for canonical rule metadata transport."""

from dataclasses import replace

import pytest

from fensu.cli._helpers.rule_metadata import rule_metadata_value
from fensu.rules.authoring.models import RuleSpec
from fensu.rules.catalog.constants import CORE_RULES
from tests.unit.src.fensu.cli._helpers._test_types import RuleMetadataCacheabilityTestCase


@pytest.mark.parametrize(
    "test_case",
    [
        RuleMetadataCacheabilityTestCase(
            description="undeclared cacheability remains null",
            cacheable=None,
            expected_cacheable=None,
        ),
        RuleMetadataCacheabilityTestCase(
            description="explicit cacheability opt-out remains false",
            cacheable=False,
            expected_cacheable=False,
        ),
        RuleMetadataCacheabilityTestCase(
            description="explicit cacheability promise remains true",
            cacheable=True,
            expected_cacheable=True,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_cacheability_state_when_serializing_metadata_then_preserves_tristate(
    test_case: RuleMetadataCacheabilityTestCase,
) -> None:
    rule: RuleSpec = replace(CORE_RULES[0], cacheable=test_case.cacheable)

    value: dict[str, object] = rule_metadata_value(rule=rule, current={})

    assert value["cacheable"] is test_case.expected_cacheable
    assert value["analyzers"] == ["python"]
