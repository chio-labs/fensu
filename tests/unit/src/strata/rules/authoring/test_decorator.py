"""Tests for the @rule decorator authoring style."""

from __future__ import annotations

import pytest

from strata.rules.authoring.constants import _RULE_SPEC_ATTRIBUTE
from strata.rules.authoring.exceptions import RuleDefinitionError
from strata.rules.authoring.main.define import rule
from strata.rules.authoring.models import RuleSpec
from strata.rules.authoring.types import ExecutionOwner, Family, RuleCheck, RuleKind
from tests.unit.src.strata.rules.authoring._test_types import (
    InvalidEnvelopeTestCase,
    RuleCacheableFlagTestCase,
    RuleEnvelopeTestCase,
    RuleExecutionOwnerTestCase,
)
from tests.unit.src.strata.rules.authoring.helpers import empty_check


@pytest.mark.parametrize(
    "test_case",
    [
        RuleEnvelopeTestCase(
            description="core SF code registers as a core rule",
            code="SFR001",
            family=Family.ROLES,
            slug="models-content",
            message="models.py must contain only models",
            expected_code="SFR001",
            expected_family=Family.ROLES,
            expected_kind=RuleKind.CORE,
        ),
        RuleEnvelopeTestCase(
            description="custom X code with custom family registers as a custom rule",
            code="XWH001",
            family=Family.CUSTOM,
            slug="warehouse-n-plus-one",
            message="warehouse metadata call inside a loop",
            expected_code="XWH001",
            expected_family=Family.CUSTOM,
            expected_kind=RuleKind.CUSTOM,
        ),
        RuleEnvelopeTestCase(
            description="custom X code may declare a core family for selection",
            code="XLA001",
            family=Family.LAYERS,
            slug="warehouse-import-boundary",
            message="warehouse import boundary crossed",
            expected_code="XLA001",
            expected_family=Family.LAYERS,
            expected_kind=RuleKind.CUSTOM,
        ),
        RuleEnvelopeTestCase(
            description="string family resolves to the matching Family member",
            code="XEV001",
            family="hygiene",
            slug="events-comment",
            message="events must not carry inline comments",
            expected_code="XEV001",
            expected_family=Family.HYGIENE,
            expected_kind=RuleKind.CUSTOM,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_valid_envelope_when_decorating_then_registers_expected_spec(
    test_case: RuleEnvelopeTestCase,
) -> None:
    decorated: RuleCheck = rule(
        code=test_case.code,
        family=test_case.family,
        slug=test_case.slug,
        message=test_case.message,
    )(empty_check)
    spec: RuleSpec = getattr(decorated, _RULE_SPEC_ATTRIBUTE)

    assert spec.code == test_case.expected_code
    assert spec.family == test_case.expected_family
    assert spec.kind == test_case.expected_kind
    assert spec.execution_owner is test_case.expected_execution_owner


@pytest.mark.parametrize(
    "test_case",
    [
        RuleExecutionOwnerTestCase(
            description="explicit domain owner is recorded on the compiled rule",
            execution_owner=ExecutionOwner.DOMAIN,
            expected_execution_owner=ExecutionOwner.DOMAIN,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_execution_owner_when_decorating_then_records_explicit_owner(
    test_case: RuleExecutionOwnerTestCase,
) -> None:
    decorated: RuleCheck = rule(
        code="XOW001",
        family=Family.CUSTOM,
        slug="execution-owner",
        message="owner",
        execution_owner=test_case.execution_owner,
    )(empty_check)
    spec: RuleSpec = getattr(decorated, _RULE_SPEC_ATTRIBUTE)

    assert spec.execution_owner is test_case.expected_execution_owner


@pytest.mark.parametrize(
    "test_case",
    [
        RuleEnvelopeTestCase(
            description="decorated function is returned unchanged and used as the check",
            code="XRT001",
            family=Family.CUSTOM,
            slug="return-check",
            message="m",
            expected_code="XRT001",
            expected_family=Family.CUSTOM,
            expected_kind=RuleKind.CUSTOM,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_valid_envelope_when_decorating_then_returns_original_function(
    test_case: RuleEnvelopeTestCase,
) -> None:
    decorated: RuleCheck = rule(
        code=test_case.code,
        family=test_case.family,
        slug=test_case.slug,
        message=test_case.message,
    )(empty_check)
    spec: RuleSpec = getattr(decorated, _RULE_SPEC_ATTRIBUTE)

    assert decorated is empty_check
    assert spec.check is empty_check
    assert spec.code == test_case.expected_code


@pytest.mark.parametrize(
    "test_case",
    [
        InvalidEnvelopeTestCase(
            description="custom family with core SF code is rejected as shadowing",
            code="SFZ001",
            family=Family.CUSTOM,
            slug="shadow",
            message="m",
            expected_error_fragment="custom family",
        ),
        InvalidEnvelopeTestCase(
            description="non-kebab slug is rejected",
            code="XKB001",
            family=Family.CUSTOM,
            slug="Not_Kebab",
            message="m",
            expected_error_fragment="kebab-case",
        ),
        InvalidEnvelopeTestCase(
            description="unknown family string is rejected",
            code="XFM001",
            family="not-a-family",
            slug="ok-slug",
            message="m",
            expected_error_fragment="family",
        ),
        InvalidEnvelopeTestCase(
            description="empty message is rejected",
            code="XMS001",
            family=Family.CUSTOM,
            slug="ok-slug",
            message="",
            expected_error_fragment="message",
        ),
        InvalidEnvelopeTestCase(
            description="empty slug is rejected",
            code="XSL001",
            family=Family.CUSTOM,
            slug="",
            message="m",
            expected_error_fragment="slug",
        ),
        InvalidEnvelopeTestCase(
            description="selector-only custom namespace is rejected as a code",
            code="XDB",
            family=Family.CUSTOM,
            slug="exact-code",
            message="m",
            expected_error_fragment="exact",
        ),
        InvalidEnvelopeTestCase(
            description="legacy hyphenated custom code is rejected",
            code="XDB-001",
            family=Family.CUSTOM,
            slug="exact-code",
            message="m",
            expected_error_fragment="exact",
        ),
        InvalidEnvelopeTestCase(
            description="lowercase custom code is rejected",
            code="Xdb001",
            family=Family.CUSTOM,
            slug="exact-code",
            message="m",
            expected_error_fragment="exact",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_invalid_envelope_when_decorating_then_raises_rule_definition_error(
    test_case: InvalidEnvelopeTestCase,
) -> None:
    with pytest.raises(RuleDefinitionError) as error:
        rule(
            code=test_case.code,
            family=test_case.family,
            slug=test_case.slug,
            message=test_case.message,
        )(empty_check)

    assert test_case.expected_error_fragment in str(error.value)


@pytest.mark.parametrize(
    "test_case",
    [
        InvalidEnvelopeTestCase(
            description="omitting a required keyword raises TypeError",
            code="XKW001",
            family=Family.CUSTOM,
            slug="ok-slug",
            message="m",
            expected_error_fragment="code",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_missing_required_keyword_when_decorating_then_raises_type_error(
    test_case: InvalidEnvelopeTestCase,
) -> None:
    with pytest.raises(TypeError) as error:
        rule(  # ty: ignore[missing-argument]
            family=test_case.family,
            slug=test_case.slug,
            message=test_case.message,
        )

    assert test_case.expected_error_fragment in str(error.value)


@pytest.mark.parametrize(
    "test_case",
    [
        RuleCacheableFlagTestCase(
            description="declared promise records cacheable True",
            cacheable=True,
            expected_cacheable=True,
        ),
        RuleCacheableFlagTestCase(
            description="declared opt-out records cacheable False",
            cacheable=False,
            expected_cacheable=False,
        ),
        RuleCacheableFlagTestCase(
            description="undeclared cacheability stays unset",
            cacheable=None,
            expected_cacheable=None,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_cacheable_declaration_when_decorating_then_records_flag(
    test_case: RuleCacheableFlagTestCase,
) -> None:
    decorated: RuleCheck = rule(
        code="XCF001",
        family=Family.CUSTOM,
        slug="cache-flag",
        message="cache flag declaration",
        cacheable=test_case.cacheable,
    )(empty_check)
    spec: RuleSpec = getattr(decorated, _RULE_SPEC_ATTRIBUTE)

    assert spec.cacheable is test_case.expected_cacheable
