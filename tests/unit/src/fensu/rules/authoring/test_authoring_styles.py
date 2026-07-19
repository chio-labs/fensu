"""Tests for decorated rule module ownership."""

from __future__ import annotations

import ast
from types import ModuleType
from typing import cast

import pytest

from fensu.rules.authoring.constants import _RULE_SPEC_ATTRIBUTE
from fensu.rules.authoring.main._inspect import rule_specs_in_module
from fensu.rules.authoring.main.define import rule
from fensu.rules.authoring.models import Fault, RuleSpec
from fensu.rules.authoring.types import Family, RuleCheck, RuleContext
from tests.unit.src.fensu.rules.authoring._test_types import (
    DirectModuleRuleCodeTestCase,
    ModuleMetadataTestCase,
)
from tests.unit.src.fensu.rules.authoring.helpers import empty_check


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


@pytest.mark.parametrize(
    "test_case",
    [
        DirectModuleRuleCodeTestCase(
            description="unhashable malformed codes remain available for grammar validation",
            code=[],
            definition_count=1,
            expected_rule_count=1,
        ),
        DirectModuleRuleCodeTestCase(
            description="None code remains available for grammar validation",
            code=None,
            definition_count=1,
            expected_rule_count=1,
        ),
        DirectModuleRuleCodeTestCase(
            description="valid duplicate string codes remain deduplicated",
            code="XDM001",
            definition_count=2,
            expected_rule_count=1,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_direct_specs_when_inspecting_module_then_only_valid_strings_are_deduplicated(
    test_case: DirectModuleRuleCodeTestCase,
) -> None:
    module: ModuleType = ModuleType("direct_rules")
    for index in range(test_case.definition_count):

        def check(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
            return []

        check.__module__ = module.__name__
        spec: RuleSpec = RuleSpec(
            code=cast(str, test_case.code),
            family=Family.CUSTOM,
            slug=f"direct-{index}",
            message="direct",
            check=check,
        )
        _ = setattr(check, _RULE_SPEC_ATTRIBUTE, spec)
        module.__dict__[f"rule_{index}"] = check

    rules: tuple[RuleSpec, ...] = rule_specs_in_module(module=module)

    assert len(rules) == test_case.expected_rule_count
