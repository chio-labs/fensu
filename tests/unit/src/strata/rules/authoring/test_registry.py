"""Tests for the per-run authoring registry and decorator/class equivalence."""

from __future__ import annotations

import ast
from typing import ClassVar

import pytest

from strata.rules.authoring.classes.rule import Rule
from strata.rules.authoring.main.collect import collect_registered
from strata.rules.authoring.main.define import rule
from strata.rules.authoring.models import Fault, RuleContext, RuleSpec
from strata.rules.authoring.types import Family, RuleKind
from tests.unit.src.strata.rules.authoring._test_types import RuleEnvelopeTestCase
from tests.unit.src.strata.rules.authoring.helpers import empty_check


@pytest.mark.parametrize(
    "test_case",
    [
        RuleEnvelopeTestCase(
            description="collect returns registered rules then clears the registry",
            code="XRG001",
            family=Family.CUSTOM,
            slug="registry-drain",
            message="m",
            expected_code="XRG001",
            expected_family=Family.CUSTOM,
            expected_kind=RuleKind.CUSTOM,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_registered_rule_when_collecting_twice_then_second_call_is_empty(
    test_case: RuleEnvelopeTestCase,
) -> None:
    rule(
        code=test_case.code,
        family=test_case.family,
        slug=test_case.slug,
        message=test_case.message,
    )(empty_check)

    first: tuple[RuleSpec, ...] = collect_registered()
    second: tuple[RuleSpec, ...] = collect_registered()

    assert len(first) == 1
    assert first[0].code == test_case.expected_code
    assert second == ()


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
    rule(
        code=test_case.code,
        family=test_case.family,
        slug=test_case.slug,
        message=test_case.message,
    )(empty_check)
    decorator_spec: RuleSpec = collect_registered()[0]

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
