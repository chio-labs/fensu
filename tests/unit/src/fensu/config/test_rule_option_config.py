"""Tests for typed per-rule option configuration resolution."""

from __future__ import annotations

import operator
from collections.abc import MutableMapping
from typing import cast

import pytest

from fensu.config.exceptions import ConfigValidationError
from fensu.config.main.build_config_for_rules import build_config_for_rules
from fensu.config.models import Config
from fensu.rules.authoring.models import RuleOption, RuleSpec
from fensu.rules.authoring.types import RuleOptionValue
from tests.unit.src.fensu.config._test_types import (
    InvalidRuleOptionsConfigTestCase,
    RuleOptionsImmutabilityTestCase,
    RuleOptionsResolutionTestCase,
)
from tests.unit.src.fensu.config.helpers import make_config_rule

_OPTION_FREE_RULE: RuleSpec = make_config_rule(code="XOP001")
_TYPED_RULE: RuleSpec = make_config_rule(
    code="XOP002",
    options=(
        RuleOption.boolean(name="enabled", default=False),
        RuleOption.integer(name="limit", default=3, minimum=1, maximum=5),
        RuleOption.string(
            name="mode",
            default="strict",
            choices=("strict", "permissive"),
        ),
        RuleOption.string_list(name="names", default=("default",), minimum_items=1),
        RuleOption.integer_list(name="levels", default=(1,), minimum_items=1),
    ),
)
_REQUIRED_RULE: RuleSpec = make_config_rule(
    code="XOP003",
    options=(RuleOption.integer(name="required_count", required=True, minimum=0),),
)
_SECOND_RULE: RuleSpec = make_config_rule(
    code="XOP004",
    options=(RuleOption.boolean(name="enabled", default=True),),
)


@pytest.mark.parametrize(
    "test_case",
    [
        RuleOptionsResolutionTestCase(
            description="option-free config retains an empty immutable mapping",
            raw_config={"roots": ["src/pkg"]},
            rules=(),
            expected_rule_options={},
        ),
        RuleOptionsResolutionTestCase(
            description="declared defaults become current values without overrides",
            raw_config={"roots": ["src/pkg"]},
            rules=(_TYPED_RULE,),
            expected_rule_options={
                "XOP002": {
                    "enabled": False,
                    "limit": 3,
                    "mode": "strict",
                    "names": ("default",),
                    "levels": (1,),
                }
            },
        ),
        RuleOptionsResolutionTestCase(
            description="known overrides resolve every supported type canonically",
            raw_config={
                "roots": ["src/pkg"],
                "rule_options": {
                    "XOP002": {
                        "enabled": True,
                        "limit": 5,
                        "mode": "permissive",
                        "names": ["alpha", "beta"],
                        "levels": [2, 3],
                    }
                },
            },
            rules=(_TYPED_RULE,),
            expected_rule_options={
                "XOP002": {
                    "enabled": True,
                    "limit": 5,
                    "mode": "permissive",
                    "names": ("alpha", "beta"),
                    "levels": (2, 3),
                }
            },
        ),
        RuleOptionsResolutionTestCase(
            description="two rules resolve the same option name independently",
            raw_config={
                "roots": ["src/pkg"],
                "rule_options": {"XOP002": {"enabled": True}},
            },
            rules=(_TYPED_RULE, _SECOND_RULE),
            expected_rule_options={
                "XOP002": {
                    "enabled": True,
                    "limit": 3,
                    "mode": "strict",
                    "names": ("default",),
                    "levels": (1,),
                },
                "XOP004": {"enabled": True},
            },
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_rule_option_config_when_building_then_resolves_current_values(
    test_case: RuleOptionsResolutionTestCase,
) -> None:
    config: Config = build_config_for_rules(raw=test_case.raw_config, rules=test_case.rules)

    assert config.rule_options == test_case.expected_rule_options


@pytest.mark.parametrize(
    "test_case",
    [
        InvalidRuleOptionsConfigTestCase(
            description="unknown rule code is rejected",
            raw_rule_options={"XOP999": {"enabled": True}},
            rules=(_TYPED_RULE,),
            expected_error_fragment="Unknown rule option code XOP999",
        ),
        InvalidRuleOptionsConfigTestCase(
            description="table for an option-free rule is rejected",
            raw_rule_options={"XOP001": {}},
            rules=(_OPTION_FREE_RULE,),
            expected_error_fragment="Rule XOP001 does not declare any options",
        ),
        InvalidRuleOptionsConfigTestCase(
            description="unknown option name is rejected",
            raw_rule_options={"XOP002": {"unknown_name": True}},
            rules=(_TYPED_RULE,),
            expected_error_fragment="Unknown option unknown_name for rule XOP002",
        ),
        InvalidRuleOptionsConfigTestCase(
            description="boolean option rejects integer scalar",
            raw_rule_options={"XOP002": {"enabled": 1}},
            rules=(_TYPED_RULE,),
            expected_error_fragment="Rule XOP002 option enabled must be a boolean",
        ),
        InvalidRuleOptionsConfigTestCase(
            description="integer option rejects boolean scalar",
            raw_rule_options={"XOP002": {"limit": True}},
            rules=(_TYPED_RULE,),
            expected_error_fragment="Rule XOP002 option limit must be an integer",
        ),
        InvalidRuleOptionsConfigTestCase(
            description="string option rejects integer scalar",
            raw_rule_options={"XOP002": {"mode": 1}},
            rules=(_TYPED_RULE,),
            expected_error_fragment="Rule XOP002 option mode must be a string",
        ),
        InvalidRuleOptionsConfigTestCase(
            description="string-list option rejects integer member",
            raw_rule_options={"XOP002": {"names": ["alpha", 1]}},
            rules=(_TYPED_RULE,),
            expected_error_fragment="Rule XOP002 option names must be an array of strings",
        ),
        InvalidRuleOptionsConfigTestCase(
            description="integer-list option rejects boolean member",
            raw_rule_options={"XOP002": {"levels": [1, True]}},
            rules=(_TYPED_RULE,),
            expected_error_fragment="Rule XOP002 option levels must be an array of integers",
        ),
        InvalidRuleOptionsConfigTestCase(
            description="missing required option is rejected",
            raw_rule_options={},
            rules=(_REQUIRED_RULE,),
            expected_error_fragment=("Required option required_count for rule XOP003 is missing"),
        ),
        InvalidRuleOptionsConfigTestCase(
            description="integer option enforces minimum",
            raw_rule_options={"XOP002": {"limit": 0}},
            rules=(_TYPED_RULE,),
            expected_error_fragment="Rule XOP002 option limit must be at least 1",
        ),
        InvalidRuleOptionsConfigTestCase(
            description="integer option enforces maximum",
            raw_rule_options={"XOP002": {"limit": 6}},
            rules=(_TYPED_RULE,),
            expected_error_fragment="Rule XOP002 option limit must be at most 5",
        ),
        InvalidRuleOptionsConfigTestCase(
            description="string option enforces choices",
            raw_rule_options={"XOP002": {"mode": "unknown"}},
            rules=(_TYPED_RULE,),
            expected_error_fragment=("Rule XOP002 option mode must be one of: strict, permissive"),
        ),
        InvalidRuleOptionsConfigTestCase(
            description="string-list option enforces minimum items",
            raw_rule_options={"XOP002": {"names": []}},
            rules=(_TYPED_RULE,),
            expected_error_fragment=("Rule XOP002 option names must contain at least 1 item"),
        ),
        InvalidRuleOptionsConfigTestCase(
            description="integer-list option enforces minimum items",
            raw_rule_options={"XOP002": {"levels": []}},
            rules=(_TYPED_RULE,),
            expected_error_fragment=("Rule XOP002 option levels must contain at least 1 item"),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_invalid_rule_options_when_building_then_raises_validation_error(
    test_case: InvalidRuleOptionsConfigTestCase,
) -> None:
    with pytest.raises(ConfigValidationError) as error:
        build_config_for_rules(
            raw={"roots": ["src/pkg"], "rule_options": test_case.raw_rule_options},
            rules=test_case.rules,
        )

    assert test_case.expected_error_fragment in str(error.value)


@pytest.mark.parametrize(
    "test_case",
    [
        RuleOptionsImmutabilityTestCase(
            description="outer and nested mappings are defensive read-only copies",
            rule_code="XOP002",
            option_name="limit",
            original_value=3,
            replacement_value=5,
            expected_error_type=TypeError,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_nested_rule_options_when_mutating_then_config_remains_immutable(
    test_case: RuleOptionsImmutabilityTestCase,
) -> None:
    source: dict[str, dict[str, RuleOptionValue]] = {
        test_case.rule_code: {test_case.option_name: test_case.original_value}
    }
    config: Config = Config(roots=("src/pkg",), rule_options=source)
    source[test_case.rule_code][test_case.option_name] = test_case.replacement_value
    mutable_outer: MutableMapping[str, object] = cast(
        "MutableMapping[str, object]", config.rule_options
    )
    mutable_inner: MutableMapping[str, RuleOptionValue] = cast(
        "MutableMapping[str, RuleOptionValue]", config.rule_options[test_case.rule_code]
    )

    assert (
        config.rule_options[test_case.rule_code][test_case.option_name] == test_case.original_value
    )
    with pytest.raises(test_case.expected_error_type):
        operator.setitem(mutable_outer, "XOP999", {})
    with pytest.raises(test_case.expected_error_type):
        operator.setitem(
            mutable_inner,
            test_case.option_name,
            test_case.replacement_value,
        )
