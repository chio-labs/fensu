"""Parity between native SFA001 and its public custom-rule equivalent."""

from __future__ import annotations

from importlib import import_module
from types import ModuleType

import pytest

from strata import RuleCase, RuleResult, evaluate_rule
from strata.analysis.constants import NATIVE_FACT_MODULE_NAME
from strata.rules.exemplars.constants import NATIVE_CUSTOM_RULE_EQUIVALENTS
from tests.integration.src.strata.rules.exemplars.main.annotations._test_types import (
    NativeCustomRegistryTestCase,
    NativeCustomRuleParityTestCase,
)
from tests.integration.src.strata.rules.exemplars.main.annotations.helpers import (
    native_rule,
    normalized_faults,
)

_PARITY_NATIVE_CODES: frozenset[str] = frozenset({"SFA001", "SFA002", "SFA101", "SFA102", "SFA103"})


@pytest.mark.parametrize(
    "test_case",
    [
        NativeCustomRuleParityTestCase(
            description="SFA001 matches a public custom rule for ordinary and variadic parameters",
            native_code="SFA001",
            source=(
                "def run(value, *items, **kwargs) -> None:\n"
                "    return None\n\n"
                "class Service:\n"
                "    def method(self, typed: int) -> None:\n"
                "        return None\n\n"
                "async def fetch(payload) -> None:\n"
                "    return None\n"
            ),
            expected_fault_count=4,
        ),
        NativeCustomRuleParityTestCase(
            description="SFA002 matches a public custom rule for sync and async functions",
            native_code="SFA002",
            source=(
                "def run(value: int):\n"
                "    return value\n\n"
                "async def fetch(value: int):\n"
                "    return value\n"
            ),
            expected_fault_count=2,
        ),
        NativeCustomRuleParityTestCase(
            description="SFA101 matches a public custom rule for module assignments",
            native_code="SFA101",
            source="value = 1\n__version__ = '1.0'\ntyped: int = 2\n",
            expected_fault_count=1,
        ),
        NativeCustomRuleParityTestCase(
            description="SFA102 matches a public custom rule for class assignments",
            native_code="SFA102",
            source=(
                "from enum import Enum\n\n"
                "class Config:\n"
                "    value = 1\n\n"
                "class Color(Enum):\n"
                "    RED = 'red'\n"
            ),
            expected_fault_count=1,
        ),
        NativeCustomRuleParityTestCase(
            description="SFA103 matches a public custom rule for inferred and ambiguous locals",
            native_code="SFA103",
            source=(
                "def run() -> None:\n"
                "    built = build_value()\n"
                "    scalar = 1\n"
                "    missing = None\n"
                "    first = second = 1\n"
            ),
            expected_fault_count=4,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_shared_fixture_when_evaluating_native_and_custom_rules_then_faults_match(
    test_case: NativeCustomRuleParityTestCase,
) -> None:
    rule_case: RuleCase = RuleCase(
        description=test_case.description,
        source=test_case.source,
        expected_fault_count=test_case.expected_fault_count,
    )
    native_result: RuleResult = evaluate_rule(
        rule=native_rule(test_case.native_code), test_case=rule_case
    )
    custom_result: RuleResult = evaluate_rule(
        rule=NATIVE_CUSTOM_RULE_EQUIVALENTS[test_case.native_code], test_case=rule_case
    )

    assert native_result.fault_count == test_case.expected_fault_count
    assert normalized_faults(native_result.faults) == normalized_faults(custom_result.faults)


@pytest.mark.parametrize(
    "test_case",
    [
        NativeCustomRegistryTestCase(
            description="every native rule has a custom equivalent and a parity fixture",
            expected_missing_codes=(),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_native_registry_when_checking_custom_parity_then_every_rule_is_covered(
    test_case: NativeCustomRegistryTestCase,
) -> None:
    native: ModuleType = import_module(NATIVE_FACT_MODULE_NAME)
    native_codes: set[str] = {code for code, _ in native.native_rule_fact_families()}
    equivalent_codes: set[str] = set(NATIVE_CUSTOM_RULE_EQUIVALENTS)
    missing: set[str] = native_codes.symmetric_difference(equivalent_codes)
    missing.update(native_codes.symmetric_difference(_PARITY_NATIVE_CODES))

    assert tuple(sorted(missing)) == test_case.expected_missing_codes
