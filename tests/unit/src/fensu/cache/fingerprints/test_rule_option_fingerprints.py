"""Tests for typed per-rule option cache fingerprints."""

from dataclasses import replace

import pytest

from fensu.cache.fingerprints._helpers.fingerprints import (
    config_fingerprint,
    ruleset_fingerprint,
)
from fensu.cache.fingerprints.models import CacheFingerprint
from fensu.config.models import Config
from fensu.rules.authoring.models import RuleOption, RuleSpec
from tests.unit.src.fensu.cache.fingerprints._test_types import (
    RuleOptionSchemaFingerprintTestCase,
    RuleOptionsConfigFingerprintTestCase,
)
from tests.unit.src.fensu.cache.fingerprints.helpers import rule_with_message


@pytest.mark.parametrize(
    "test_case",
    [
        RuleOptionsConfigFingerprintTestCase(
            description="current scalar value change invalidates config identity",
            first_rule_options={"XCA001": {"limit": 2}},
            second_rule_options={"XCA001": {"limit": 3}},
            expected_equal=False,
        ),
        RuleOptionsConfigFingerprintTestCase(
            description="rule and option mapping insertion order preserves config identity",
            first_rule_options={
                "XCA001": {"enabled": True, "limit": 2},
                "XCA002": {"mode": "strict"},
            },
            second_rule_options={
                "XCA002": {"mode": "strict"},
                "XCA001": {"limit": 2, "enabled": True},
            },
            expected_equal=True,
        ),
        RuleOptionsConfigFingerprintTestCase(
            description="current list value order changes config identity",
            first_rule_options={"XCA001": {"labels": ("api", "worker")}},
            second_rule_options={"XCA001": {"labels": ("worker", "api")}},
            expected_equal=False,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_resolved_rule_options_when_fingerprinting_then_preserves_value_semantics(
    test_case: RuleOptionsConfigFingerprintTestCase,
) -> None:
    first: CacheFingerprint = config_fingerprint(
        Config(roots=("src/pkg",), rule_options=test_case.first_rule_options)
    )
    second: CacheFingerprint = config_fingerprint(
        Config(roots=("src/pkg",), rule_options=test_case.second_rule_options)
    )

    assert (first == second) is test_case.expected_equal


@pytest.mark.parametrize(
    "test_case",
    [
        RuleOptionSchemaFingerprintTestCase(
            description="option schema addition invalidates ruleset identity",
            first_options=(),
            second_options=(RuleOption.boolean(name="enabled", default=True),),
            expected_equal=False,
        ),
        RuleOptionSchemaFingerprintTestCase(
            description="option default change invalidates ruleset identity",
            first_options=(RuleOption.integer(name="limit", default=2),),
            second_options=(RuleOption.integer(name="limit", default=3),),
            expected_equal=False,
        ),
        RuleOptionSchemaFingerprintTestCase(
            description="option type change invalidates ruleset identity",
            first_options=(RuleOption.boolean(name="enabled", default=True),),
            second_options=(RuleOption.integer(name="enabled", default=1),),
            expected_equal=False,
        ),
        RuleOptionSchemaFingerprintTestCase(
            description="option constraint change invalidates ruleset identity",
            first_options=(RuleOption.integer(name="limit", default=2, minimum=0),),
            second_options=(RuleOption.integer(name="limit", default=2, minimum=1),),
            expected_equal=False,
        ),
        RuleOptionSchemaFingerprintTestCase(
            description="option choices order preserves ruleset identity",
            first_options=(
                RuleOption.string(
                    name="mode",
                    default="strict",
                    choices=("strict", "lenient"),
                ),
            ),
            second_options=(
                RuleOption.string(
                    name="mode",
                    default="strict",
                    choices=("lenient", "strict"),
                ),
            ),
            expected_equal=True,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_typed_rule_option_schemas_when_fingerprinting_then_preserves_schema_semantics(
    test_case: RuleOptionSchemaFingerprintTestCase,
) -> None:
    first_rule: RuleSpec = replace(
        rule_with_message("message"),
        options=test_case.first_options,
    )
    second_rule: RuleSpec = replace(
        rule_with_message("message"),
        options=test_case.second_options,
    )

    first: CacheFingerprint = ruleset_fingerprint((first_rule,))
    second: CacheFingerprint = ruleset_fingerprint((second_rule,))

    assert (first == second) is test_case.expected_equal
