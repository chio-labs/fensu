"""Tests for the public RuleOption authoring API."""

from __future__ import annotations

from functools import partial
from typing import Any, cast

import pytest

import fensu
from fensu import Family, RuleOption, rule
from fensu.rules.authoring.exceptions import RuleDefinitionError
from tests.unit.src.fensu.rules.authoring._test_types import (
    DuplicateRuleOptionTestCase,
    InvalidRuleOptionDeclarationTestCase,
    PublicRuleOptionExportTestCase,
    RuleOptionDeclarationTestCase,
)
from tests.unit.src.fensu.rules.authoring.helpers import empty_check

_RULE_OPTION_DECLARATION_CASES: tuple[RuleOptionDeclarationTestCase, ...] = (
    RuleOptionDeclarationTestCase(
        description="boolean constructor records its typed default",
        option=RuleOption.boolean(
            name="enabled",
            default=True,
            description="Enable the policy.",
        ),
        expected_name="enabled",
        expected_kind="boolean",
        expected_default=True,
        expected_description="Enable the policy.",
    ),
    RuleOptionDeclarationTestCase(
        description="integer constructor records its bounded default",
        option=RuleOption.integer(
            name="limit",
            default=3,
            minimum=1,
            maximum=5,
            description="Maximum findings.",
        ),
        expected_name="limit",
        expected_kind="integer",
        expected_default=3,
        expected_description="Maximum findings.",
    ),
    RuleOptionDeclarationTestCase(
        description="string constructor records its choice-backed default",
        option=RuleOption.string(
            name="mode",
            default="strict",
            choices=("strict", "permissive"),
            description="Policy mode.",
        ),
        expected_name="mode",
        expected_kind="string",
        expected_default="strict",
        expected_description="Policy mode.",
    ),
    RuleOptionDeclarationTestCase(
        description="string-list constructor preserves its tuple default",
        option=RuleOption.string_list(
            name="names",
            default=("alpha", "beta"),
            minimum_items=1,
            description="Selected names.",
        ),
        expected_name="names",
        expected_kind="string_list",
        expected_default=("alpha", "beta"),
        expected_description="Selected names.",
    ),
    RuleOptionDeclarationTestCase(
        description="integer-list constructor preserves its tuple default",
        option=RuleOption.integer_list(
            name="levels",
            default=(1, 2),
            minimum_items=1,
            description="Selected levels.",
        ),
        expected_name="levels",
        expected_kind="integer_list",
        expected_default=(1, 2),
        expected_description="Selected levels.",
    ),
)

_INVALID_RULE_OPTION_DECLARATION_CASES: tuple[InvalidRuleOptionDeclarationTestCase, ...] = (
    InvalidRuleOptionDeclarationTestCase(
        description="mixed-case names are rejected",
        constructor=partial(RuleOption.boolean, name="BadName", default=True),
        expected_error_fragment="lowercase snake case",
    ),
    InvalidRuleOptionDeclarationTestCase(
        description="required options cannot also define defaults",
        constructor=partial(RuleOption.boolean, name="enabled", default=True, required=True),
        expected_error_fragment="cannot be required and define a default",
    ),
    InvalidRuleOptionDeclarationTestCase(
        description="optional options must define defaults",
        constructor=partial(RuleOption.boolean, name="enabled"),
        expected_error_fragment="must define a default or be required",
    ),
    InvalidRuleOptionDeclarationTestCase(
        description="string choices cannot be empty",
        constructor=partial(RuleOption.string, name="mode", default="strict", choices=()),
        expected_error_fragment="non-empty and unique",
    ),
    InvalidRuleOptionDeclarationTestCase(
        description="string choices cannot contain duplicates",
        constructor=partial(
            RuleOption.string,
            name="mode",
            default="strict",
            choices=("strict", "strict"),
        ),
        expected_error_fragment="non-empty and unique",
    ),
    InvalidRuleOptionDeclarationTestCase(
        description="string defaults must belong to declared choices",
        constructor=partial(
            RuleOption.string,
            name="mode",
            default="unknown",
            choices=("strict", "permissive"),
        ),
        expected_error_fragment="must be one of",
    ),
    InvalidRuleOptionDeclarationTestCase(
        description="integer defaults cannot fall below their minimum",
        constructor=partial(RuleOption.integer, name="limit", default=0, minimum=1),
        expected_error_fragment="must be at least 1",
    ),
    InvalidRuleOptionDeclarationTestCase(
        description="integer defaults cannot exceed their maximum",
        constructor=partial(RuleOption.integer, name="limit", default=6, maximum=5),
        expected_error_fragment="must be at most 5",
    ),
    InvalidRuleOptionDeclarationTestCase(
        description="integer minimum cannot exceed maximum",
        constructor=partial(
            RuleOption.integer,
            name="limit",
            default=3,
            minimum=5,
            maximum=1,
        ),
        expected_error_fragment="minimum cannot exceed maximum",
    ),
    InvalidRuleOptionDeclarationTestCase(
        description="string-list defaults must use immutable tuples",
        constructor=partial(
            RuleOption.string_list,
            name="names",
            default=cast(Any, ["alpha"]),
        ),
        expected_error_fragment="must be an array of strings",
    ),
    InvalidRuleOptionDeclarationTestCase(
        description="integer-list defaults must use immutable tuples",
        constructor=partial(
            RuleOption.integer_list,
            name="levels",
            default=cast(Any, [1]),
        ),
        expected_error_fragment="must be an array of integers",
    ),
    InvalidRuleOptionDeclarationTestCase(
        description="list defaults must satisfy their item bound",
        constructor=partial(
            RuleOption.string_list,
            name="names",
            default=(),
            minimum_items=1,
        ),
        expected_error_fragment="must contain at least 1 item",
    ),
)


@pytest.mark.parametrize(
    "test_case",
    [
        RuleOptionDeclarationTestCase(**vars(test_case))
        for test_case in _RULE_OPTION_DECLARATION_CASES
    ],
    ids=lambda case: case.description,
)
def test_given_public_constructor_when_declaring_option_then_records_typed_value(
    test_case: RuleOptionDeclarationTestCase,
) -> None:
    assert test_case.option.name == test_case.expected_name
    assert test_case.option.kind.value == test_case.expected_kind
    assert test_case.option.default == test_case.expected_default
    assert test_case.option.description == test_case.expected_description
    assert test_case.option.required is test_case.expected_required


@pytest.mark.parametrize(
    "test_case",
    [
        InvalidRuleOptionDeclarationTestCase(**vars(test_case))
        for test_case in _INVALID_RULE_OPTION_DECLARATION_CASES
    ],
    ids=lambda case: case.description,
)
def test_given_invalid_public_option_when_declaring_then_raises_definition_error(
    test_case: InvalidRuleOptionDeclarationTestCase,
) -> None:
    with pytest.raises(RuleDefinitionError) as error:
        test_case.constructor()

    assert test_case.expected_error_fragment in str(error.value)


@pytest.mark.parametrize(
    "test_case",
    [
        DuplicateRuleOptionTestCase(
            description="one rule cannot declare the same option name twice",
            options=(
                RuleOption.boolean(name="enabled", default=True),
                RuleOption.boolean(name="enabled", default=False),
            ),
            expected_error_fragment="duplicate option names",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_duplicate_option_names_when_decorating_rule_then_raises_definition_error(
    test_case: DuplicateRuleOptionTestCase,
) -> None:
    with pytest.raises(RuleDefinitionError) as error:
        rule(
            code="XOP001",
            family=Family.CUSTOM,
            slug="duplicate-options",
            message="duplicate options",
            options=test_case.options,
        )(empty_check)

    assert test_case.expected_error_fragment in str(error.value)


@pytest.mark.parametrize(
    "test_case",
    [
        PublicRuleOptionExportTestCase(
            description="RuleOption is available from the top-level package",
            attribute_name="RuleOption",
            expected_export=RuleOption,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_fensu_package_when_reading_rule_option_then_exposes_public_type(
    test_case: PublicRuleOptionExportTestCase,
) -> None:
    assert getattr(fensu, test_case.attribute_name) is test_case.expected_export
    assert test_case.attribute_name in fensu.__all__
