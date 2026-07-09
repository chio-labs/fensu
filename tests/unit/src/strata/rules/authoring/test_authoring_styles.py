"""Tests for decorator and class rule authoring equivalence."""

from __future__ import annotations

import ast
from types import ModuleType
from typing import ClassVar

import pytest

from strata.rules.authoring.classes.rule import Rule
from strata.rules.authoring.constants import _RULE_SPEC_ATTRIBUTE
from strata.rules.authoring.main.define import rule
from strata.rules.authoring.main.inspect import rule_specs_in_module
from strata.rules.authoring.models import Fault, RuleSpec
from strata.rules.authoring.types import Family, RuleCheck, RuleContext, RuleKind
from tests.unit.src.strata.rules.authoring._test_types import (
    ModuleMetadataTestCase,
    RuleEnvelopeTestCase,
)
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


@pytest.mark.parametrize(
    "test_case",
    [
        RuleEnvelopeTestCase(
            description="decorator and class produce equivalent spec metadata",
            code="XEQ001",
            family=Family.CUSTOM,
            slug="equivalent-spec",
            message="equivalent metadata",
            expected_code="XEQ001",
            expected_family=Family.CUSTOM,
            expected_kind=RuleKind.CUSTOM,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_same_metadata_when_authoring_both_styles_then_specs_are_equivalent(
    test_case: RuleEnvelopeTestCase,
) -> None:
    decorated: RuleCheck = rule(
        code=test_case.code,
        family=test_case.family,
        slug=test_case.slug,
        message=test_case.message,
    )(empty_check)
    decorator_spec: RuleSpec = getattr(decorated, _RULE_SPEC_ATTRIBUTE)

    class EquivalentRule(Rule):
        code: ClassVar[str] = test_case.code
        family: ClassVar[Family | str] = test_case.family
        slug: ClassVar[str] = test_case.slug
        message: ClassVar[str] = test_case.message

        def check(self, module: ast.Module, ctx: RuleContext) -> list[Fault]:
            return []

    class_spec: RuleSpec = EquivalentRule().to_spec()

    assert decorator_spec.code == class_spec.code == test_case.expected_code
    assert decorator_spec.family == class_spec.family == test_case.expected_family
    assert decorator_spec.kind == class_spec.kind == test_case.expected_kind
    assert decorator_spec.slug == class_spec.slug
    assert decorator_spec.message == class_spec.message
    assert decorator_spec.severity == class_spec.severity
    assert decorator_spec.enabled_by_default == class_spec.enabled_by_default
