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

_PARITY_NATIVE_CODES: frozenset[str] = frozenset(
    {
        "SFA001",
        "SFA002",
        "SFA101",
        "SFA102",
        "SFA103",
        "SFH001",
        "SFH002",
        "SFH003",
        "SFH004",
        "SFH005",
        "SFH006",
        "SFH007",
        "SFH008",
        "SFH009",
        "SFS110",
        "SFS130",
        "SFS131",
    }
)


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
        NativeCustomRuleParityTestCase(
            description="SFH001 matches a public custom rule for multiline docstrings",
            native_code="SFH001",
            source='"""Summary.\n\nDetails.\n"""\n',
            expected_fault_count=1,
        ),
        NativeCustomRuleParityTestCase(
            description="SFH002 matches a public custom rule for standalone comments",
            native_code="SFH002",
            source="# explain the branch\n# noqa: E501\nvalue: int = 1\n",
            expected_fault_count=1,
        ),
        NativeCustomRuleParityTestCase(
            description="SFH003 matches a public custom rule for raw built-in raises",
            native_code="SFH003",
            source="def run() -> None:\n    raise ValueError('bad')\n",
            expected_fault_count=1,
        ),
        NativeCustomRuleParityTestCase(
            description="SFH004 matches a public custom rule for runtime assertions",
            native_code="SFH004",
            source="def run(value: int) -> None:\n    assert value > 0\n",
            expected_fault_count=1,
        ),
        NativeCustomRuleParityTestCase(
            description="SFH005 matches a public custom rule for swallowed probes",
            native_code="SFH005",
            source=(
                "def exists() -> bool | None:\n"
                "    try:\n"
                "        return bool(object())\n"
                "    except Exception:\n"
                "        return None\n"
            ),
            expected_fault_count=1,
        ),
        NativeCustomRuleParityTestCase(
            description="SFH006 matches a public custom rule in tooling scope",
            native_code="SFH006",
            source="pairs = [(left, right) for left in (1, 2) for right in (3, 4)]\n",
            expected_fault_count=1,
            path="scripts/check.py",
            scope="tooling",
            scope_root="scripts",
        ),
        NativeCustomRuleParityTestCase(
            description="SFH007 matches a public custom rule for string decisions",
            native_code="SFH007",
            source="def ready(status: str) -> bool:\n    return status in {'ready', 'done'}\n",
            expected_fault_count=2,
        ),
        NativeCustomRuleParityTestCase(
            description="SFH008 matches a public custom rule for magic numeric comparisons",
            native_code="SFH008",
            source="def ready(value: int) -> bool:\n    return value == 42\n",
            expected_fault_count=1,
        ),
        NativeCustomRuleParityTestCase(
            description="SFH009 matches a public custom rule for import-time calls",
            native_code="SFH009",
            source="configure()\n",
            expected_fault_count=1,
        ),
        NativeCustomRuleParityTestCase(
            description="SFS110 matches a public custom rule for unreturned mutations",
            native_code="SFS110",
            source=(
                "def update(left: list[int], right: list[int]) -> list[int]:\n"
                "    left.append(1)\n"
                "    right.append(2)\n"
                "    return left\n"
            ),
            expected_fault_count=1,
        ),
        NativeCustomRuleParityTestCase(
            description="SFS130 matches a public custom rule for outer-state mutations",
            native_code="SFS130",
            source="CACHE: list[int] = []\n\ndef run() -> None:\n    CACHE.append(1)\n",
            expected_fault_count=1,
        ),
        NativeCustomRuleParityTestCase(
            description="SFS131 matches a public custom rule for complex comprehensions",
            native_code="SFS131",
            source="pairs = [(left, right) for left in (1, 2) for right in (3, 4)]\n",
            expected_fault_count=1,
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
        path=test_case.path,
        scope=test_case.scope,
        scope_root=test_case.scope_root,
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
