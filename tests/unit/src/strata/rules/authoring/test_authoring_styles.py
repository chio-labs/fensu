"""Tests for decorated rule module ownership."""

from __future__ import annotations

from types import ModuleType

import pytest

from strata.rules.authoring.main.define import rule
from strata.rules.authoring.main.inspect import rule_specs_in_module
from strata.rules.authoring.models import RuleSpec
from strata.rules.authoring.types import Family, RuleCheck
from tests.unit.src.strata.rules.authoring._test_types import ModuleMetadataTestCase
from tests.unit.src.strata.rules.authoring.helpers import empty_check


@pytest.mark.parametrize(
    "test_case",
    [
        ModuleMetadataTestCase(
            description="imported decorated functions are not owned rule definitions",
            expected_codes=(),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_module_with_foreign_decorated_function_when_inspecting_then_ignores_import(
    test_case: ModuleMetadataTestCase,
) -> None:
    decorated: RuleCheck = rule(
        code="XFR001",
        family=Family.CUSTOM,
        slug="foreign-rule",
        message="foreign",
    )(empty_check)
    module: ModuleType = ModuleType("custom_consumer")
    module.__dict__["foreign_rule"] = decorated

    rules: tuple[RuleSpec, ...] = rule_specs_in_module(module=module)

    assert tuple(spec.code for spec in rules) == test_case.expected_codes
