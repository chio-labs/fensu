"""Parity between native SFA001 and its public custom-rule equivalent."""

from __future__ import annotations

from importlib import import_module
from types import ModuleType

import pytest

from strata import RuleCase, RuleFile, RuleResult, evaluate_rule
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
        "SFL001",
        "SFL002",
        "SFL101",
        "SFL102",
        "SFL103",
        "SFL104",
        "SFL105",
        "SFL110",
        "SFL301",
        "SFN001",
        "SFN002",
        "SFN003",
        "SFN004",
        "SFS001",
        "SFS002",
        "SFS003",
        "SFS010",
        "SFS011",
        "SFS101",
        "SFS102",
        "SFS110",
        "SFS120",
        "SFS130",
        "SFS131",
        "SFS201",
        "SFR001",
        "SFR002",
        "SFR003",
        "SFR004",
        "SFR101",
        "SFR102",
        "SFR103",
        "SFR104",
        "SFR201",
        "SFR202",
        "SFR203",
        "SFR204",
        "SFR205",
        "SFR301",
        "SFR302",
        "SFR303",
        "SFR304",
        "SFR305",
        "SFR306",
        "SFR307",
        "SFR308",
        "SFR309",
        "SFR401",
        "SFR402",
        "SFR403",
        "SFR404",
        "SFR405",
        "SFR406",
        "SFR501",
        "SFR502",
        "SFR503",
        "SFR601",
        "SFR701",
        "SFR702",
        "SFR703",
        "SFR704",
        "SFR705",
        "SFR706",
        "SFR707",
        "SFT001",
        "SFT002",
        "SFT003",
        "SFT004",
        "SFT005",
        "SFT006",
        "SFT007",
        "SFT008",
        "SFT101",
        "SFT102",
        "SFT103",
        "SFT104",
        "SFT105",
        "SFT106",
        "SFT201",
        "SFT202",
        "SFT203",
        "SFT204",
        "SFT301",
        "SFT302",
        "SFT401",
        "SFT402",
        "SFT403",
        "SFT404",
        "SFT405",
        "SFT406",
        "SFT407",
        "SFT408",
        "SFT411",
        "SFT412",
        "SFT413",
        "SFT414",
    }
)
_PYTHON_OWNED_SFR_CODES: frozenset[str] = frozenset()


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
            description="SFL001 matches a public custom rule for relative imports",
            native_code="SFL001",
            source="from ..models import Result\n",
            expected_fault_count=1,
            path="src/example/_helpers/example.py",
        ),
        NativeCustomRuleParityTestCase(
            description="SFL002 matches a public custom rule for star imports",
            native_code="SFL002",
            source="from example.models import *\n",
            expected_fault_count=1,
            path="src/example/_helpers/example.py",
        ),
        NativeCustomRuleParityTestCase(
            description="SFL110 matches a public custom rule for qualified helper-private classes",
            native_code="SFL110",
            source="from example._helpers import parsing\nvalue = parsing._Cursor()\n",
            expected_fault_count=1,
            path="src/example/main/example.py",
        ),
        NativeCustomRuleParityTestCase(
            description="SFL001 native and custom routing both exclude test scope",
            native_code="SFL001",
            source="from .helpers import build_case\n",
            expected_fault_count=0,
            path="tests/unit/src/example/test_example.py",
            scope="test",
            scope_root="tests",
        ),
        NativeCustomRuleParityTestCase(
            description="SFL002 native and custom routing both exclude test scope",
            native_code="SFL002",
            source="from example.helpers import *\n",
            expected_fault_count=0,
            path="tests/unit/src/example/test_example.py",
            scope="test",
            scope_root="tests",
        ),
        NativeCustomRuleParityTestCase(
            description="SFL110 native and custom routing both exclude test scope",
            native_code="SFL110",
            source="from example._helpers.parsing import _Cursor\n",
            expected_fault_count=0,
            path="tests/unit/src/example/test_example.py",
            scope="test",
            scope_root="tests",
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
        NativeCustomRuleParityTestCase(
            description="SFR001 matches foreign declarations in models role files",
            native_code="SFR001",
            source="def build() -> None:\n    return None\n",
            expected_fault_count=1,
            path="src/example/models.py",
        ),
        NativeCustomRuleParityTestCase(
            description="SFR002 matches runtime declarations in types role files",
            native_code="SFR002",
            source="def build() -> None:\n    return None\n",
            expected_fault_count=1,
            path="src/example/types.py",
        ),
        NativeCustomRuleParityTestCase(
            description="SFR003 matches class declarations in constants role files",
            native_code="SFR003",
            source="class Config:\n    value: int\n",
            expected_fault_count=1,
            path="src/example/constants.py",
        ),
        NativeCustomRuleParityTestCase(
            description="SFR004 matches non-exception declarations in exceptions role files",
            native_code="SFR004",
            source="class Result:\n    value: int\n",
            expected_fault_count=1,
            path="src/example/exceptions.py",
        ),
        NativeCustomRuleParityTestCase(
            description="SFR101 matches model declarations outside the models role",
            native_code="SFR101",
            source=(
                "from dataclasses import dataclass\n\n"
                "@dataclass(frozen=True)\nclass Result:\n    value: int\n"
            ),
            expected_fault_count=1,
            path="src/example/_helpers/results.py",
        ),
        NativeCustomRuleParityTestCase(
            description="SFR102 matches public type declarations outside the types role",
            native_code="SFR102",
            source="from typing import Protocol\n\nclass Service(Protocol):\n    value: int\n",
            expected_fault_count=1,
            path="src/example/main/example.py",
        ),
        NativeCustomRuleParityTestCase(
            description="SFR103 matches public constants outside the constants role",
            native_code="SFR103",
            source="MAX_ITEMS: int = 3\n",
            expected_fault_count=1,
            path="src/example/_helpers/example.py",
        ),
        NativeCustomRuleParityTestCase(
            description="SFR104 matches exception declarations outside the exceptions role",
            native_code="SFR104",
            source="class ConfigError(Exception):\n    pass\n",
            expected_fault_count=1,
            path="src/example/_helpers/example.py",
        ),
        NativeCustomRuleParityTestCase(
            description="SFR201 matches generic module filenames",
            native_code="SFR201",
            source="value: int = 1\n",
            expected_fault_count=1,
            path="src/example/_helpers/misc.py",
        ),
        NativeCustomRuleParityTestCase(
            description="SFR202 matches legacy helpers module filenames",
            native_code="SFR202",
            source="value: int = 1\n",
            expected_fault_count=1,
            path="src/example/helpers.py",
        ),
        NativeCustomRuleParityTestCase(
            description="SFR203 matches monolithic classes module filenames",
            native_code="SFR203",
            source="class Service:\n    pass\n",
            expected_fault_count=1,
            path="src/example/classes.py",
        ),
        NativeCustomRuleParityTestCase(
            description="SFR205 matches public plain helper classes",
            native_code="SFR205",
            source="class Cursor:\n    pass\n",
            expected_fault_count=1,
            path="src/example/_helpers/parsing.py",
        ),
        NativeCustomRuleParityTestCase(
            description="SFR303 matches reserved role filenames beneath helpers",
            native_code="SFR303",
            source="value: int = 1\n",
            expected_fault_count=1,
            path="src/example/_helpers/models.py",
        ),
        NativeCustomRuleParityTestCase(
            description="SFR304 matches ad hoc modules directly beneath nested packages",
            native_code="SFR304",
            source="value: int = 1\n",
            expected_fault_count=1,
            path="src/example/orders/work/value.py",
        ),
        NativeCustomRuleParityTestCase(
            description="SFR305 matches arbitrary nested subpackages without role boundaries",
            native_code="SFR305",
            source="value: int = 1\n",
            expected_fault_count=1,
            path="src/example/orders/work/detail/value.py",
        ),
        NativeCustomRuleParityTestCase(
            description="SFR307 matches ad hoc direct modules in top-level domains",
            native_code="SFR307",
            source="value: int = 1\n",
            expected_fault_count=1,
            path="src/example/orders/value.py",
        ),
        NativeCustomRuleParityTestCase(
            description="SFR401 matches entry modules without one public function",
            native_code="SFR401",
            source="def _prepare() -> None:\n    return None\n",
            expected_fault_count=1,
            path="src/example/main/example.py",
        ),
        NativeCustomRuleParityTestCase(
            description="SFR402 matches nonempty nested package initializers",
            native_code="SFR402",
            source="value: int = 1\n",
            expected_fault_count=1,
            path="src/example/_helpers/__init__.py",
        ),
        NativeCustomRuleParityTestCase(
            description="SFR403 matches internal pure re-export shims",
            native_code="SFR403",
            source="from example.models import Result\n\n__all__ = ['Result']\n",
            expected_fault_count=1,
            path="src/example/result.py",
        ),
        NativeCustomRuleParityTestCase(
            description="SFR404 matches helper all declarations",
            native_code="SFR404",
            source="__all__: list[str] = []\n",
            expected_fault_count=1,
            path="src/example/_helpers/example.py",
        ),
        NativeCustomRuleParityTestCase(
            description="SFR406 matches runtime declarations on root package surfaces",
            native_code="SFR406",
            source="value: int = 1\n",
            expected_fault_count=1,
            path="src/example/__init__.py",
        ),
        NativeCustomRuleParityTestCase(
            description="SFR501 matches classes modules with multiple top-level classes",
            native_code="SFR501",
            source="class First:\n    pass\n\nclass Second:\n    pass\n",
            expected_fault_count=1,
            path="src/example/classes/service.py",
        ),
        NativeCustomRuleParityTestCase(
            description="SFR502 matches main modules beneath helpers packages",
            native_code="SFR502",
            source="def run() -> None:\n    return None\n",
            expected_fault_count=1,
            path="src/example/_helpers/main.py",
        ),
        NativeCustomRuleParityTestCase(
            description="SFR601 matches source files above their Python-resolved line limit",
            native_code="SFR601",
            source="first: int = 1\nsecond: int = 2\n",
            expected_fault_count=1,
            path="src/example/_helpers/example.py",
            config={"thresholds": {"max_file_lines": 1}},
        ),
        NativeCustomRuleParityTestCase(
            description="SFR601 preserves Python splitlines semantics for local source text",
            native_code="SFR601",
            source="# first\x0c# second\nvalue: int = 1\n",
            expected_fault_count=1,
            path="src/example/_helpers/example.py",
            config={"thresholds": {"max_file_lines": 2}},
        ),
        NativeCustomRuleParityTestCase(
            description="SFR701 matches unsupported direct-script functions",
            native_code="SFR701",
            source="def parse_args() -> object:\n    return object()\n\ndef main() -> int:\n    return 0\n",
            expected_fault_count=1,
            path="scripts/report.py",
            scope="tooling",
            scope_root="scripts",
        ),
        NativeCustomRuleParityTestCase(
            description="SFR702 matches direct scripts without imported main delegation",
            native_code="SFR702",
            source="def main() -> int:\n    return 0\n",
            expected_fault_count=1,
            path="scripts/report.py",
            scope="tooling",
            scope_root="scripts",
        ),
        NativeCustomRuleParityTestCase(
            description="SFR703 matches direct scripts above their Python-resolved line limit",
            native_code="SFR703",
            source="def main() -> int:\n    return 0\n",
            expected_fault_count=1,
            path="scripts/report.py",
            scope="tooling",
            scope_root="scripts",
            config={"thresholds": {"max_script_entrypoint_lines": 1}},
        ),
        NativeCustomRuleParityTestCase(
            description="SFR704 matches undecorated declarations in tooling rules modules",
            native_code="SFR704",
            source="def helper() -> None:\n    return None\n",
            expected_fault_count=1,
            path="scripts/example/rules/imports.py",
            scope="tooling",
            scope_root="scripts",
        ),
        NativeCustomRuleParityTestCase(
            description="SFR706 matches rule-code tooling module filenames",
            native_code="SFR706",
            source="",
            expected_fault_count=1,
            path="scripts/example/rules/sft104.py",
            scope="tooling",
            scope_root="scripts",
        ),
        NativeCustomRuleParityTestCase(
            description="SFR503 matches dynamic private declaration messages and locations",
            native_code="SFR503",
            source=(
                "from dataclasses import dataclass\n\n"
                "def run() -> None:\n    return None\n\n"
                "@dataclass(frozen=True)\nclass _State:\n    value: int\n\n"
                "_VALUE: int = 1\n"
            ),
            expected_fault_count=2,
            path="src/example/_helpers/example.py",
        ),
        NativeCustomRuleParityTestCase(
            description="SFR503 native and custom routing both exclude test scope",
            native_code="SFR503",
            source="def run() -> None:\n    return None\n\n_VALUE: int = 1\n",
            expected_fault_count=0,
            path="tests/unit/src/example/test_example.py",
            scope="test",
            scope_root="tests",
        ),
        NativeCustomRuleParityTestCase(
            description="SFT101 matches a public custom rule for nonempty test package modules",
            native_code="SFT101",
            source="value: int = 1\n",
            expected_fault_count=1,
            path="tests/unit/src/example/__init__.py",
            scope="test",
            scope_root="tests",
        ),
        NativeCustomRuleParityTestCase(
            description="SFT102 matches a public custom rule for relative test imports",
            native_code="SFT102",
            source="from .helpers import build_case\n",
            expected_fault_count=1,
            path="tests/unit/src/example/test_example.py",
            scope="test",
            scope_root="tests",
        ),
        NativeCustomRuleParityTestCase(
            description="SFT103 matches a public custom rule for top-level test helpers",
            native_code="SFT103",
            source="def helper() -> None:\n    return None\n",
            expected_fault_count=1,
            path="tests/unit/src/example/test_example.py",
            scope="test",
            scope_root="tests",
        ),
        NativeCustomRuleParityTestCase(
            description="SFT104 matches a public custom rule for test function conditionals",
            native_code="SFT104",
            source=(
                "def test_given_value_when_checking_then_matches() -> None:\n"
                "    if True:\n"
                "        pass\n"
            ),
            expected_fault_count=1,
            path="tests/unit/src/example/test_example.py",
            scope="test",
            scope_root="tests",
        ),
        NativeCustomRuleParityTestCase(
            description="SFT105 matches a public custom rule for private constants after tests",
            native_code="SFT105",
            source=(
                "def test_given_value_when_checking_then_matches() -> None:\n"
                "    return None\n\n_PRIVATE: int = 1\n"
            ),
            expected_fault_count=1,
            path="tests/unit/src/example/test_example.py",
            scope="test",
            scope_root="tests",
        ),
        NativeCustomRuleParityTestCase(
            description="SFT106 matches a public custom rule for complex test comprehensions",
            native_code="SFT106",
            source="pairs = [(left, right) for left in (1, 2) for right in (3, 4)]\n",
            expected_fault_count=1,
            path="tests/unit/src/example/test_example.py",
            scope="test",
            scope_root="tests",
        ),
        NativeCustomRuleParityTestCase(
            description="SFT201 matches a public custom rule for missing test-case descriptions",
            native_code="SFT201",
            source=(
                "from dataclasses import dataclass\n\n"
                "@dataclass(frozen=True)\nclass Case:\n    expected_value: int\n"
            ),
            expected_fault_count=1,
            path="tests/unit/src/example/_test_types.py",
            scope="test",
            scope_root="tests",
        ),
        NativeCustomRuleParityTestCase(
            description="SFT202 matches a public custom rule for missing expected fields",
            native_code="SFT202",
            source=(
                "from dataclasses import dataclass\n\n"
                "@dataclass(frozen=True)\nclass Case:\n    description: str\n"
            ),
            expected_fault_count=1,
            path="tests/unit/src/example/_test_types.py",
            scope="test",
            scope_root="tests",
        ),
        NativeCustomRuleParityTestCase(
            description="SFT203 matches a public custom rule for foreign local test-type imports",
            native_code="SFT203",
            source="from tests.unit.src.other._test_types import Case\n",
            expected_fault_count=1,
            path="tests/unit/src/example/test_example.py",
            scope="test",
            scope_root="tests",
        ),
        NativeCustomRuleParityTestCase(
            description="SFT301 matches a public custom rule for test module filenames",
            native_code="SFT301",
            source="",
            expected_fault_count=1,
            path="tests/unit/src/example/example.py",
            scope="test",
            scope_root="tests",
        ),
        NativeCustomRuleParityTestCase(
            description="SFT302 matches a public custom rule for test function names",
            native_code="SFT302",
            source="def test_bad_name() -> None:\n    return None\n",
            expected_fault_count=1,
            path="tests/unit/src/example/test_example.py",
            scope="test",
            scope_root="tests",
        ),
        NativeCustomRuleParityTestCase(
            description="SFT401 matches a public custom rule for missing parameterization",
            native_code="SFT401",
            source=(
                "def test_given_value_when_checking_then_matches() -> None:\n    return None\n"
            ),
            expected_fault_count=1,
            path="tests/unit/src/example/test_example.py",
            scope="test",
            scope_root="tests",
        ),
        NativeCustomRuleParityTestCase(
            description="SFT402 matches a public custom rule for missing test_case parameters",
            native_code="SFT402",
            source=(
                "@pytest.mark.parametrize('test_case', [Case()], ids=lambda case: case.description)\n"
                "def test_given_value_when_checking_then_matches(case: Case) -> None:\n"
                "    return None\n"
            ),
            expected_fault_count=1,
            path="tests/unit/src/example/test_example.py",
            scope="test",
            scope_root="tests",
        ),
        NativeCustomRuleParityTestCase(
            description="SFT404 matches a public custom rule for missing expected-field references",
            native_code="SFT404",
            source=(
                "@pytest.mark.parametrize('test_case', [Case()], ids=lambda case: case.description)\n"
                "def test_given_value_when_checking_then_matches(test_case: Case) -> None:\n"
                "    assert True\n"
            ),
            expected_fault_count=1,
            path="tests/unit/src/example/test_example.py",
            scope="test",
            scope_root="tests",
        ),
        NativeCustomRuleParityTestCase(
            description="SFT405 matches a public custom rule for missing parametrize values",
            native_code="SFT405",
            source=(
                "@pytest.mark.parametrize('test_case')\n"
                "def test_given_value_when_checking_then_matches(test_case: Case) -> None:\n"
                "    return None\n"
            ),
            expected_fault_count=1,
            path="tests/unit/src/example/test_example.py",
            scope="test",
            scope_root="tests",
        ),
        NativeCustomRuleParityTestCase(
            description="SFT406 matches a public custom rule for wrong parametrize parameter names",
            native_code="SFT406",
            source=(
                "@pytest.mark.parametrize('case', [Case()], ids=lambda case: case.description)\n"
                "def test_given_value_when_checking_then_matches(case: Case) -> None:\n"
                "    return None\n"
            ),
            expected_fault_count=1,
            path="tests/unit/src/example/test_example.py",
            scope="test",
            scope_root="tests",
        ),
        NativeCustomRuleParityTestCase(
            description="SFT407 matches a public custom rule for missing parametrize ids",
            native_code="SFT407",
            source=(
                "@pytest.mark.parametrize('test_case', [Case()])\n"
                "def test_given_value_when_checking_then_matches(test_case: Case) -> None:\n"
                "    return None\n"
            ),
            expected_fault_count=1,
            path="tests/unit/src/example/test_example.py",
            scope="test",
            scope_root="tests",
        ),
        NativeCustomRuleParityTestCase(
            description="SFT408 matches a public custom rule for indirect parametrize values",
            native_code="SFT408",
            source=(
                "@pytest.mark.parametrize('test_case', CASES, ids=lambda case: case.description)\n"
                "def test_given_value_when_checking_then_matches(test_case: Case) -> None:\n"
                "    return None\n"
            ),
            expected_fault_count=1,
            path="tests/unit/src/example/test_example.py",
            scope="test",
            scope_root="tests",
        ),
        NativeCustomRuleParityTestCase(
            description="SFT411 matches a public custom rule for empty parametrize values",
            native_code="SFT411",
            source=(
                "@pytest.mark.parametrize('test_case', [], ids=lambda case: case.description)\n"
                "def test_given_value_when_checking_then_matches(test_case: Case) -> None:\n"
                "    return None\n"
            ),
            expected_fault_count=1,
            path="tests/unit/src/example/test_example.py",
            scope="test",
            scope_root="tests",
        ),
        NativeCustomRuleParityTestCase(
            description="SFT412 matches a public custom rule for dictionary test cases",
            native_code="SFT412",
            source=(
                "@pytest.mark.parametrize('test_case', [{}], ids=lambda case: case.description)\n"
                "def test_given_value_when_checking_then_matches(test_case: Case) -> None:\n"
                "    return None\n"
            ),
            expected_fault_count=1,
            path="tests/unit/src/example/test_example.py",
            scope="test",
            scope_root="tests",
        ),
        NativeCustomRuleParityTestCase(
            description="SFT414 matches a public custom rule for non-description ids",
            native_code="SFT414",
            source=(
                "@pytest.mark.parametrize('test_case', [Case()], ids=['case'])\n"
                "def test_given_value_when_checking_then_matches(test_case: Case) -> None:\n"
                "    return None\n"
            ),
            expected_fault_count=1,
            path="tests/unit/src/example/test_example.py",
            scope="test",
            scope_root="tests",
        ),
        NativeCustomRuleParityTestCase(
            description="SFL103 matches a public custom rule for bare package imports",
            native_code="SFL103",
            source="from example import PublicModel\nimport example as public_api\n",
            expected_fault_count=2,
        ),
        NativeCustomRuleParityTestCase(
            description="SFL301 matches a public custom rule for configured tooling imports",
            native_code="SFL301",
            source="from scripts.release import publish\nimport scripts.formatting as formatting\n",
            expected_fault_count=2,
            files=(
                RuleFile(path="scripts/release.py", source="def publish() -> None:\n    pass\n"),
            ),
        ),
        NativeCustomRuleParityTestCase(
            description="SFT102 native and custom routing both exclude runtime scope",
            native_code="SFT102",
            source="from .helpers import build_case\n",
            expected_fault_count=0,
        ),
        NativeCustomRuleParityTestCase(
            description="SFS101 matches public project function resolution",
            native_code="SFS101",
            source="from example._helpers.phase import load\n\ndef run() -> None:\n    load()\n",
            expected_fault_count=1,
            files=(
                RuleFile(
                    path="src/example/_helpers/phase.py",
                    source="def load() -> int:\n    return 1\n",
                ),
            ),
        ),
        NativeCustomRuleParityTestCase(
            description="SFL101 matches public sibling package observations",
            native_code="SFL101",
            source="from example.domain.beta._helpers import load\n",
            expected_fault_count=1,
            path="src/example/domain/alpha/main/run.py",
        ),
        NativeCustomRuleParityTestCase(
            description="SFL102 matches public cross-domain package observations",
            native_code="SFL102",
            source="from example.other._helpers import load\n",
            expected_fault_count=1,
            path="src/example/domain/main/run.py",
        ),
        NativeCustomRuleParityTestCase(
            description="SFL104 matches public module existence observations",
            native_code="SFL104",
            source="from example.other.main._load import load\n",
            expected_fault_count=1,
            path="src/example/domain/main/run.py",
            files=(
                RuleFile(
                    path="src/example/other/main/_load.py", source="def load() -> None:\n    pass\n"
                ),
            ),
        ),
        NativeCustomRuleParityTestCase(
            description="SFR204 matches public namespace package anchors",
            native_code="SFR204",
            source="",
            expected_fault_count=1,
            path="src/example/shared/__init__.py",
        ),
        NativeCustomRuleParityTestCase(
            description="SFL105 matches public project import graph observations",
            native_code="SFL105",
            source="def run() -> None:\n    pass\n",
            expected_fault_count=1,
            path="src/example/domain/main/run.py",
        ),
        NativeCustomRuleParityTestCase(
            description="SFR301 matches public helpers package observations",
            native_code="SFR301",
            source="",
            expected_fault_count=0,
            path="src/example/domain/_helpers/__init__.py",
        ),
        NativeCustomRuleParityTestCase(
            description="SFR302 matches public main package observations",
            native_code="SFR302",
            source="",
            expected_fault_count=0,
            path="src/example/domain/main/__init__.py",
        ),
        NativeCustomRuleParityTestCase(
            description="SFR306 matches public domain shape observations",
            native_code="SFR306",
            source="",
            expected_fault_count=0,
            path="src/example/domain/models.py",
        ),
        NativeCustomRuleParityTestCase(
            description="SFR308 matches public scope prefix observations",
            native_code="SFR308",
            source="",
            expected_fault_count=0,
            path="src/example/domain/models.py",
        ),
        NativeCustomRuleParityTestCase(
            description="SFR309 matches public leaf main observations",
            native_code="SFR309",
            source="def run() -> None:\n    pass\n",
            expected_fault_count=0,
            path="src/example/domain/main/run.py",
        ),
        NativeCustomRuleParityTestCase(
            description="SFR405 matches public sibling directory observations",
            native_code="SFR405",
            source="def run() -> None:\n    pass\n",
            expected_fault_count=1,
            path="src/example/main/run.py",
            files=(RuleFile(path="src/example/main/run/__init__.py", source=""),),
        ),
        NativeCustomRuleParityTestCase(
            description="SFR705 matches public tooling package anchors",
            native_code="SFR705",
            source="",
            expected_fault_count=1,
            path="scripts/tool/misc/__init__.py",
            scope="tooling",
            scope_root="scripts",
        ),
        NativeCustomRuleParityTestCase(
            description="SFR707 native and public routing agree without registrations",
            native_code="SFR707",
            source="",
            expected_fault_count=0,
        ),
        NativeCustomRuleParityTestCase(
            description="SFT001 matches public shallow test layout decisions",
            native_code="SFT001",
            source="",
            expected_fault_count=1,
            path="tests/test_example.py",
            scope="test",
            scope_root="tests",
        ),
        NativeCustomRuleParityTestCase(
            description="SFT002 matches public test scope decisions",
            native_code="SFT002",
            source="",
            expected_fault_count=1,
            path="tests/slow/src/example/test_example.py",
            scope="test",
            scope_root="tests",
        ),
        NativeCustomRuleParityTestCase(
            description="SFT003 matches public mirror root decisions",
            native_code="SFT003",
            source="",
            expected_fault_count=1,
            path="tests/unit/docs/example/test_example.py",
            scope="test",
            scope_root="tests",
        ),
        NativeCustomRuleParityTestCase(
            description="SFT004 matches public runtime mirror depth decisions",
            native_code="SFT004",
            source="",
            expected_fault_count=1,
            path="tests/unit/src/example/test_example.py",
            scope="test",
            scope_root="tests",
            files=(RuleFile(path="src/example/__init__.py", source=""),),
        ),
        NativeCustomRuleParityTestCase(
            description="SFT005 matches public source package decisions",
            native_code="SFT005",
            source="",
            expected_fault_count=1,
            path="tests/unit/src/other/core/test_example.py",
            scope="test",
            scope_root="tests",
            files=(RuleFile(path="src/example/__init__.py", source=""),),
        ),
        NativeCustomRuleParityTestCase(
            description="SFT006 matches public runtime area observations",
            native_code="SFT006",
            source="",
            expected_fault_count=1,
            path="tests/unit/src/example/missing/test_example.py",
            scope="test",
            scope_root="tests",
            files=(RuleFile(path="src/example/__init__.py", source=""),),
        ),
        NativeCustomRuleParityTestCase(
            description="SFT007 matches public tooling mirror depth decisions",
            native_code="SFT007",
            source="",
            expected_fault_count=1,
            path="tests/unit/scripts/test_example.py",
            scope="test",
            scope_root="tests",
            files=(RuleFile(path="scripts/tool.py", source=""),),
        ),
        NativeCustomRuleParityTestCase(
            description="SFT008 matches public tooling area observations",
            native_code="SFT008",
            source="",
            expected_fault_count=1,
            path="tests/unit/scripts/missing/test_example.py",
            scope="test",
            scope_root="tests",
            files=(RuleFile(path="scripts/tool.py", source=""),),
        ),
        NativeCustomRuleParityTestCase(
            description="SFT204 matches public sibling file observations",
            native_code="SFT204",
            source="",
            expected_fault_count=1,
            path="tests/unit/src/example/test_example.py",
            scope="test",
            scope_root="tests",
        ),
        NativeCustomRuleParityTestCase(
            description="SFT403 matches public sibling dataclass facts",
            native_code="SFT403",
            source=(
                "import pytest\nfrom tests.unit.src.example._test_types import Case\n"
                "@pytest.mark.parametrize('test_case', [Case()])\n"
                "def test_given_value_when_checking_then_matches(test_case: object) -> None:\n    pass\n"
            ),
            expected_fault_count=1,
            path="tests/unit/src/example/test_example.py",
            scope="test",
            scope_root="tests",
            files=(
                RuleFile(
                    path="tests/unit/src/example/_test_types.py",
                    source="from dataclasses import dataclass\n@dataclass\nclass Case:\n    value: int\n",
                ),
            ),
        ),
        NativeCustomRuleParityTestCase(
            description="SFT413 matches public local constructor facts",
            native_code="SFT413",
            source=(
                "import pytest\nfrom tests.unit.src.example._test_types import Case\n"
                "@pytest.mark.parametrize('test_case', [object()])\n"
                "def test_given_value_when_checking_then_matches(test_case: Case) -> None:\n    pass\n"
            ),
            expected_fault_count=1,
            path="tests/unit/src/example/test_example.py",
            scope="test",
            scope_root="tests",
            files=(
                RuleFile(
                    path="tests/unit/src/example/_test_types.py",
                    source="from dataclasses import dataclass\n@dataclass\nclass Case:\n    value: int\n",
                ),
            ),
        ),
        NativeCustomRuleParityTestCase(
            description="SFT106 native and custom routing both exclude runtime scope",
            native_code="SFT106",
            source="pairs = [(left, right) for left in (1, 2) for right in (3, 4)]\n",
            expected_fault_count=0,
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
        files=test_case.files,
    )
    native_result: RuleResult = evaluate_rule(
        rule=native_rule(test_case.native_code), test_case=rule_case
    )
    custom_result: RuleResult = evaluate_rule(
        rule=NATIVE_CUSTOM_RULE_EQUIVALENTS[test_case.native_code], test_case=rule_case
    )

    assert native_result.fault_count == test_case.expected_fault_count
    assert normalized_faults(native_result.faults) == normalized_faults(custom_result.faults)
    assert native_result.dependencies == custom_result.dependencies


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
    missing.update(native_codes.intersection(_PYTHON_OWNED_SFR_CODES))

    assert tuple(sorted(missing)) == test_case.expected_missing_codes
