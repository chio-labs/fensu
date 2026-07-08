"""Tests for the Rule class authoring style and its definition-time validation."""

from __future__ import annotations

import ast
from typing import ClassVar

import pytest

from strata.rules.authoring.classes.rule import Rule
from strata.rules.authoring.exceptions import RuleDefinitionError
from strata.rules.authoring.models import Fault, RuleSpec
from strata.rules.authoring.types import Family, RuleContext, RuleKind, Severity
from tests.unit.src.strata.rules.authoring._test_types import (
    InvalidEnvelopeTestCase,
    RuleEnvelopeTestCase,
)


@pytest.mark.parametrize(
    "test_case",
    [
        RuleEnvelopeTestCase(
            description="core class rule compiles to a core spec",
            code="SFS001",
            family=Family.SHAPE,
            slug="max-statements",
            message="function too long",
            expected_code="SFS001",
            expected_family=Family.SHAPE,
            expected_kind=RuleKind.CORE,
        ),
        RuleEnvelopeTestCase(
            description="custom class rule compiles to a custom spec",
            code="XWH002",
            family=Family.CUSTOM,
            slug="warehouse-scan",
            message="warehouse scan detected",
            expected_code="XWH002",
            expected_family=Family.CUSTOM,
            expected_kind=RuleKind.CUSTOM,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_valid_subclass_when_compiling_then_produces_expected_spec(
    test_case: RuleEnvelopeTestCase,
) -> None:
    class ConcreteRule(Rule):
        code: ClassVar[str] = test_case.code
        family: ClassVar[Family | str] = test_case.family
        slug: ClassVar[str] = test_case.slug
        message: ClassVar[str] = test_case.message

        def check(self, module: ast.Module, ctx: RuleContext) -> list[Fault]:
            return []

    spec: RuleSpec = ConcreteRule().to_spec()

    assert spec.code == test_case.expected_code
    assert spec.family == test_case.expected_family
    assert spec.kind == test_case.expected_kind


@pytest.mark.parametrize(
    "test_case",
    [
        InvalidEnvelopeTestCase(
            description="subclass missing the message class attribute is rejected at definition",
            code="SFS002",
            family=Family.SHAPE,
            slug="ok-slug",
            message="unused",
            expected_error_fragment="message",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_subclass_missing_classvar_when_defined_then_raises_rule_definition_error(
    test_case: InvalidEnvelopeTestCase,
) -> None:
    with pytest.raises(RuleDefinitionError) as error:

        class MissingMessageRule(Rule):
            code: ClassVar[str] = test_case.code
            family: ClassVar[Family | str] = test_case.family
            slug: ClassVar[str] = test_case.slug

            def check(self, module: ast.Module, ctx: RuleContext) -> list[Fault]:
                return []

    assert test_case.expected_error_fragment in str(error.value)


@pytest.mark.parametrize(
    "test_case",
    [
        InvalidEnvelopeTestCase(
            description="custom-family subclass with core code is rejected at definition",
            code="SFZ002",
            family=Family.CUSTOM,
            slug="shadow-class",
            message="m",
            expected_error_fragment="custom family",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_shadowing_subclass_when_defined_then_raises_rule_definition_error(
    test_case: InvalidEnvelopeTestCase,
) -> None:
    with pytest.raises(RuleDefinitionError) as error:

        class ShadowRule(Rule):
            code: ClassVar[str] = test_case.code
            family: ClassVar[Family | str] = test_case.family
            slug: ClassVar[str] = test_case.slug
            message: ClassVar[str] = test_case.message

            def check(self, module: ast.Module, ctx: RuleContext) -> list[Fault]:
                return []

    assert test_case.expected_error_fragment in str(error.value)


@pytest.mark.parametrize(
    "test_case",
    [
        RuleEnvelopeTestCase(
            description="class default severity is error",
            code="SFS003",
            family=Family.SHAPE,
            slug="default-severity",
            message="m",
            expected_code="SFS003",
            expected_family=Family.SHAPE,
            expected_kind=RuleKind.CORE,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_subclass_without_severity_when_compiling_then_defaults_to_error(
    test_case: RuleEnvelopeTestCase,
) -> None:
    class DefaultSeverityRule(Rule):
        code: ClassVar[str] = test_case.code
        family: ClassVar[Family | str] = test_case.family
        slug: ClassVar[str] = test_case.slug
        message: ClassVar[str] = test_case.message

        def check(self, module: ast.Module, ctx: RuleContext) -> list[Fault]:
            return []

    spec: RuleSpec = DefaultSeverityRule().to_spec()

    assert spec.severity == Severity.ERROR
    assert spec.code == test_case.expected_code
