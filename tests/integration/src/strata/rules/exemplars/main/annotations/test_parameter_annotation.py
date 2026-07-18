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
        "SFN001",
        "SFN002",
        "SFN003",
        "SFN004",
        "SFS001",
        "SFS002",
        "SFS003",
        "SFS010",
        "SFS011",
        "SFS102",
        "SFS110",
        "SFS120",
        "SFS130",
        "SFS131",
        "SFS201",
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
            description="SFN001 matches default and custom no-return contracts",
            native_code="SFN001",
            source=(
                "def validate_config() -> bool:\n    return True\n\n"
                "def ensure_ready() -> int:\n    return 1\n\n"
                "def validate_clean() -> None:\n    return None\n"
            ),
            expected_fault_count=2,
            config={"contracts": {"ensure_*": "no-return"}},
        ),
        NativeCustomRuleParityTestCase(
            description="SFN002 matches accepted categories and dynamic predicate remediations",
            native_code="SFN002",
            source=(
                "from typing import TypeGuard\n\n"
                "def is_ready() -> Status:\n    return Status()\n\n"
                "def has_items() -> int:\n    return 1\n\n"
                "def can_retry() -> str:\n    return 'no'\n\n"
                "def supports_mode() -> Mode:\n    return Mode()\n\n"
                "def is_narrow(value: object) -> TypeGuard[int]:\n    return True\n\n"
                "def has_missing():\n    return True\n"
            ),
            expected_fault_count=4,
        ),
        NativeCustomRuleParityTestCase(
            description="SFN002 preserves fnmatchcase classes case and same-behavior overlap",
            native_code="SFN002",
            source=(
                "def Ready() -> Status:\n    return Status()\n\n"
                "def ready() -> Status:\n    return Status()\n"
            ),
            expected_fault_count=1,
            config={
                "contracts": {
                    "[R]eady": "returns-bool",
                    "R*": "returns-bool",
                }
            },
        ),
        NativeCustomRuleParityTestCase(
            description="SFN002 preserves fnmatchcase ranges negation invalid ranges and Unicode",
            native_code="SFN002",
            source=(
                "def Check_alpha() -> Status:\n    return Status()\n\n"
                "def check_x() -> Status:\n    return Status()\n\n"
                "def check_beta() -> Status:\n    return Status()\n\n"
                "def check_zeta() -> Status:\n    return Status()\n\n"
                "def État() -> Status:\n    return Status()\n"
            ),
            expected_fault_count=4,
            config={
                "contracts": {
                    "Check_*": "returns-bool",
                    "check_?": "returns-bool",
                    "check_[ab]eta": "returns-bool",
                    "check_[!z]eta": "returns-bool",
                    "check_[z-a]eta": "returns-bool",
                    "[É]tat": "returns-bool",
                }
            },
        ),
        NativeCustomRuleParityTestCase(
            description="SFN003 matches query conversion and custom value contracts",
            native_code="SFN003",
            source=(
                "def get_user() -> None:\n    return None\n\n"
                "def to_user() -> NoReturn:\n    raise RuntimeError\n\n"
                "def fetch_user() -> None:\n    return None\n\n"
                "def as_record() -> Record:\n    return Record()\n"
            ),
            expected_fault_count=3,
            config={"contracts": {"fetch_*": "returns-value"}},
        ),
        NativeCustomRuleParityTestCase(
            description="SFN004 matches yields accepted iterators and eager custom streams",
            native_code="SFN004",
            source=(
                "from collections.abc import Iterator\n\n"
                "def iter_rows() -> list[int]:\n    return []\n\n"
                "def iter_owned() -> list[int]:\n    yield 1\n\n"
                "def iter_declared() -> Iterator[int]:\n    return iter(())\n\n"
                "def stream_rows() -> tuple[int, ...]:\n    return ()\n"
            ),
            expected_fault_count=2,
            config={"contracts": {"stream_*": "returns-iterator"}},
        ),
        NativeCustomRuleParityTestCase(
            description="SFS001 matches a public custom rule with a compact statement threshold",
            native_code="SFS001",
            source="def run() -> None:\n    value: int = 1\n    return None\n",
            expected_fault_count=1,
            config={"thresholds": {"max_statements": 1}},
        ),
        NativeCustomRuleParityTestCase(
            description="SFS001 native and custom guards both exclude non-main modules",
            native_code="SFS001",
            source="def run() -> None:\n    value: int = 1\n    return None\n",
            expected_fault_count=0,
            path="src/example/_helpers/example.py",
            config={"thresholds": {"max_statements": 1}},
        ),
        NativeCustomRuleParityTestCase(
            description="SFS002 matches a public custom rule with a compact call threshold",
            native_code="SFS002",
            source=(
                "def first() -> None:\n    return None\n\n"
                "def second() -> None:\n    return None\n\n"
                "def run() -> None:\n    first()\n    second()\n"
            ),
            expected_fault_count=1,
            config={"thresholds": {"max_distinct_calls": 1}},
        ),
        NativeCustomRuleParityTestCase(
            description="SFS002 native and custom guards both exclude non-main modules",
            native_code="SFS002",
            source="def run() -> None:\n    first()\n    second()\n",
            expected_fault_count=0,
            path="src/example/_helpers/example.py",
            config={"thresholds": {"max_distinct_calls": 1}},
        ),
        NativeCustomRuleParityTestCase(
            description="SFS003 matches a public custom rule with a compact local threshold",
            native_code="SFS003",
            source="def run() -> None:\n    first: int = 1\n    second: int = 2\n",
            expected_fault_count=1,
            config={"thresholds": {"max_locals": 1}},
        ),
        NativeCustomRuleParityTestCase(
            description="SFS003 native and custom guards both exclude non-main modules",
            native_code="SFS003",
            source="def run() -> None:\n    first: int = 1\n    second: int = 2\n",
            expected_fault_count=0,
            path="src/example/_helpers/example.py",
            config={"thresholds": {"max_locals": 1}},
        ),
        NativeCustomRuleParityTestCase(
            description="SFS010 matches a public custom rule with a compact argument threshold",
            native_code="SFS010",
            source="def run(first: int, second: int) -> None:\n    return None\n",
            expected_fault_count=1,
            path="src/example/_helpers/example.py",
            config={"thresholds": {"max_arguments": 1}},
        ),
        NativeCustomRuleParityTestCase(
            description="SFS011 leaves top-level main ownership to SFS001 but checks methods",
            native_code="SFS011",
            source=(
                "def run() -> None:\n    value: int = 1\n    return None\n\n"
                "class Service:\n"
                "    def run(self) -> None:\n"
                "        value: int = 1\n"
                "        return None\n"
            ),
            expected_fault_count=1,
            config={"thresholds": {"max_statements_global": 1}},
        ),
        NativeCustomRuleParityTestCase(
            description="SFS102 matches a public custom rule for helper parameter mutation",
            native_code="SFS102",
            source="def update(values: list[int]) -> None:\n    values.append(1)\n",
            expected_fault_count=1,
            path="src/example/_helpers/example.py",
        ),
        NativeCustomRuleParityTestCase(
            description="SFS102 native and custom guards both exclude non-helper modules",
            native_code="SFS102",
            source="def update(values: list[int]) -> None:\n    values.append(1)\n",
            expected_fault_count=0,
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
            description="SFS120 matches a public custom rule with a compact positional threshold",
            native_code="SFS120",
            source="def run(first: int, second: int) -> None:\n    return None\n",
            expected_fault_count=1,
            path="src/example/_helpers/example.py",
            config={"thresholds": {"max_positional_args": 1}},
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
        NativeCustomRuleParityTestCase(
            description="SFS201 matches a public custom rule for mutable dataclass models",
            native_code="SFS201",
            source=(
                "from dataclasses import dataclass\n\n@dataclass\nclass Result:\n    value: int\n"
            ),
            expected_fault_count=1,
            path="src/example/models.py",
        ),
        NativeCustomRuleParityTestCase(
            description="SFS201 native and custom guards both exclude non-model modules",
            native_code="SFS201",
            source=(
                "from dataclasses import dataclass\n\n@dataclass\nclass Result:\n    value: int\n"
            ),
            expected_fault_count=0,
            path="src/example/_helpers/example.py",
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
        config=test_case.config,
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
