"""Parity between native FFA001 and its public custom-rule equivalent."""

from __future__ import annotations

from importlib import import_module
from types import ModuleType

import pytest

from fensu import RuleCase, RuleFile, RuleResult, evaluate_rule
from fensu.analysis.constants import NATIVE_FACT_MODULE_NAME
from fensu.rules.exemplars.constants import NATIVE_CUSTOM_RULE_EQUIVALENTS
from tests.integration.src.fensu.rules.exemplars.main.annotations._test_types import (
    NativeCustomRegistryTestCase,
    NativeCustomRuleParityTestCase,
)
from tests.integration.src.fensu.rules.exemplars.main.annotations.helpers import (
    native_rule,
    normalized_faults,
)

_PARITY_NATIVE_CODES: frozenset[str] = frozenset(
    {
        "FFA001",
        "FFA002",
        "FFA101",
        "FFA102",
        "FFA103",
        "FFH001",
        "FFH002",
        "FFH003",
        "FFH004",
        "FFH005",
        "FFH006",
        "FFH007",
        "FFH008",
        "FFH009",
        "FFL001",
        "FFL002",
        "FFL101",
        "FFL102",
        "FFL103",
        "FFL104",
        "FFL105",
        "FFL110",
        "FFL301",
        "FFN001",
        "FFN002",
        "FFN003",
        "FFN004",
        "FFS001",
        "FFS002",
        "FFS003",
        "FFS010",
        "FFS011",
        "FFS101",
        "FFS102",
        "FFS110",
        "FFS120",
        "FFS130",
        "FFS131",
        "FFS201",
        "FFR001",
        "FFR002",
        "FFR003",
        "FFR004",
        "FFR101",
        "FFR102",
        "FFR103",
        "FFR104",
        "FFR201",
        "FFR202",
        "FFR203",
        "FFR204",
        "FFR205",
        "FFR301",
        "FFR302",
        "FFR303",
        "FFR304",
        "FFR305",
        "FFR306",
        "FFR307",
        "FFR308",
        "FFR309",
        "FFR401",
        "FFR402",
        "FFR403",
        "FFR404",
        "FFR405",
        "FFR406",
        "FFR501",
        "FFR502",
        "FFR503",
        "FFR601",
        "FFR701",
        "FFR702",
        "FFR703",
        "FFR704",
        "FFR705",
        "FFR706",
        "FFR707",
        "FFT001",
        "FFT002",
        "FFT003",
        "FFT004",
        "FFT005",
        "FFT006",
        "FFT007",
        "FFT008",
        "FFT101",
        "FFT102",
        "FFT103",
        "FFT104",
        "FFT105",
        "FFT106",
        "FFT201",
        "FFT202",
        "FFT203",
        "FFT204",
        "FFT301",
        "FFT302",
        "FFT401",
        "FFT402",
        "FFT403",
        "FFT404",
        "FFT405",
        "FFT406",
        "FFT407",
        "FFT408",
        "FFT411",
        "FFT412",
        "FFT413",
        "FFT414",
    }
)
_PYTHON_OWNED_SFR_CODES: frozenset[str] = frozenset()


@pytest.mark.parametrize(
    "test_case",
    [
        NativeCustomRuleParityTestCase(
            description="FFA001 matches a public custom rule for ordinary and variadic parameters",
            native_code="FFA001",
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
            description="FFA002 matches a public custom rule for sync and async functions",
            native_code="FFA002",
            source=(
                "def run(value: int):\n"
                "    return value\n\n"
                "async def fetch(value: int):\n"
                "    return value\n"
            ),
            expected_fault_count=2,
        ),
        NativeCustomRuleParityTestCase(
            description="FFA101 matches a public custom rule for module assignments",
            native_code="FFA101",
            source="value = 1\n__version__ = '1.0'\ntyped: int = 2\n",
            expected_fault_count=1,
        ),
        NativeCustomRuleParityTestCase(
            description="FFA102 matches a public custom rule for class assignments",
            native_code="FFA102",
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
            description="FFA103 matches a public custom rule for inferred and ambiguous locals",
            native_code="FFA103",
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
            description="FFH001 matches a public custom rule for multiline docstrings",
            native_code="FFH001",
            source='"""Summary.\n\nDetails.\n"""\n',
            expected_fault_count=1,
        ),
        NativeCustomRuleParityTestCase(
            description="FFH002 matches a public custom rule for standalone comments",
            native_code="FFH002",
            source="# explain the branch\n# noqa: E501\nvalue: int = 1\n",
            expected_fault_count=1,
        ),
        NativeCustomRuleParityTestCase(
            description="FFH003 matches a public custom rule for raw built-in raises",
            native_code="FFH003",
            source="def run() -> None:\n    raise ValueError('bad')\n",
            expected_fault_count=1,
        ),
        NativeCustomRuleParityTestCase(
            description="FFH004 matches a public custom rule for runtime assertions",
            native_code="FFH004",
            source="def run(value: int) -> None:\n    assert value > 0\n",
            expected_fault_count=1,
        ),
        NativeCustomRuleParityTestCase(
            description="FFH005 matches a public custom rule for swallowed probes",
            native_code="FFH005",
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
            description="FFH006 matches a public custom rule in tooling scope",
            native_code="FFH006",
            source="pairs = [(left, right) for left in (1, 2) for right in (3, 4)]\n",
            expected_fault_count=1,
            path="scripts/check.py",
            scope="tooling",
            scope_root="scripts",
        ),
        NativeCustomRuleParityTestCase(
            description="FFH007 matches a public custom rule for string decisions",
            native_code="FFH007",
            source="def ready(status: str) -> bool:\n    return status in {'ready', 'done'}\n",
            expected_fault_count=2,
        ),
        NativeCustomRuleParityTestCase(
            description="FFH008 matches a public custom rule for magic numeric comparisons",
            native_code="FFH008",
            source="def ready(value: int) -> bool:\n    return value == 42\n",
            expected_fault_count=1,
        ),
        NativeCustomRuleParityTestCase(
            description="FFH009 matches a public custom rule for import-time calls",
            native_code="FFH009",
            source="configure()\n",
            expected_fault_count=1,
        ),
        NativeCustomRuleParityTestCase(
            description="FFL001 matches a public custom rule for relative imports",
            native_code="FFL001",
            source="from ..models import Result\n",
            expected_fault_count=1,
            path="src/example/_helpers/example.py",
        ),
        NativeCustomRuleParityTestCase(
            description="FFL002 matches a public custom rule for star imports",
            native_code="FFL002",
            source="from example.models import *\n",
            expected_fault_count=1,
            path="src/example/_helpers/example.py",
        ),
        NativeCustomRuleParityTestCase(
            description="FFL110 matches a public custom rule for qualified helper-private classes",
            native_code="FFL110",
            source="from example._helpers import parsing\nvalue = parsing._Cursor()\n",
            expected_fault_count=1,
            path="src/example/main/example.py",
        ),
        NativeCustomRuleParityTestCase(
            description="FFL001 native and custom routing both exclude test scope",
            native_code="FFL001",
            source="from .helpers import build_case\n",
            expected_fault_count=0,
            path="tests/unit/src/example/test_example.py",
            scope="test",
            scope_root="tests",
        ),
        NativeCustomRuleParityTestCase(
            description="FFL002 native and custom routing both exclude test scope",
            native_code="FFL002",
            source="from example.helpers import *\n",
            expected_fault_count=0,
            path="tests/unit/src/example/test_example.py",
            scope="test",
            scope_root="tests",
        ),
        NativeCustomRuleParityTestCase(
            description="FFL110 native and custom routing both exclude test scope",
            native_code="FFL110",
            source="from example._helpers.parsing import _Cursor\n",
            expected_fault_count=0,
            path="tests/unit/src/example/test_example.py",
            scope="test",
            scope_root="tests",
        ),
        NativeCustomRuleParityTestCase(
            description="FFN001 matches default and custom no-return contracts",
            native_code="FFN001",
            source=(
                "def validate_config() -> bool:\n    return True\n\n"
                "def ensure_ready() -> int:\n    return 1\n\n"
                "def validate_clean() -> None:\n    return None\n"
            ),
            expected_fault_count=2,
            config={"contracts": {"ensure_*": "no-return"}},
        ),
        NativeCustomRuleParityTestCase(
            description="FFN002 matches accepted categories and dynamic predicate remediations",
            native_code="FFN002",
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
            description="FFN002 preserves fnmatchcase classes case and same-behavior overlap",
            native_code="FFN002",
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
            description="FFN002 preserves fnmatchcase ranges negation invalid ranges and Unicode",
            native_code="FFN002",
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
            description="FFN003 matches query conversion and custom value contracts",
            native_code="FFN003",
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
            description="FFN004 matches yields accepted iterators and eager custom streams",
            native_code="FFN004",
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
            description="FFS001 matches a public custom rule with a compact statement threshold",
            native_code="FFS001",
            source="def run() -> None:\n    value: int = 1\n    return None\n",
            expected_fault_count=1,
            config={"thresholds": {"max_statements": 1}},
        ),
        NativeCustomRuleParityTestCase(
            description="FFS001 native and custom guards both exclude non-main modules",
            native_code="FFS001",
            source="def run() -> None:\n    value: int = 1\n    return None\n",
            expected_fault_count=0,
            path="src/example/_helpers/example.py",
            config={"thresholds": {"max_statements": 1}},
        ),
        NativeCustomRuleParityTestCase(
            description="FFS002 matches a public custom rule with a compact call threshold",
            native_code="FFS002",
            source=(
                "def first() -> None:\n    return None\n\n"
                "def second() -> None:\n    return None\n\n"
                "def run() -> None:\n    first()\n    second()\n"
            ),
            expected_fault_count=1,
            config={"thresholds": {"max_distinct_calls": 1}},
        ),
        NativeCustomRuleParityTestCase(
            description="FFS002 native and custom guards both exclude non-main modules",
            native_code="FFS002",
            source="def run() -> None:\n    first()\n    second()\n",
            expected_fault_count=0,
            path="src/example/_helpers/example.py",
            config={"thresholds": {"max_distinct_calls": 1}},
        ),
        NativeCustomRuleParityTestCase(
            description="FFS003 matches a public custom rule with a compact local threshold",
            native_code="FFS003",
            source="def run() -> None:\n    first: int = 1\n    second: int = 2\n",
            expected_fault_count=1,
            config={"thresholds": {"max_locals": 1}},
        ),
        NativeCustomRuleParityTestCase(
            description="FFS003 native and custom guards both exclude non-main modules",
            native_code="FFS003",
            source="def run() -> None:\n    first: int = 1\n    second: int = 2\n",
            expected_fault_count=0,
            path="src/example/_helpers/example.py",
            config={"thresholds": {"max_locals": 1}},
        ),
        NativeCustomRuleParityTestCase(
            description="FFS010 matches a public custom rule with a compact argument threshold",
            native_code="FFS010",
            source="def run(first: int, second: int) -> None:\n    return None\n",
            expected_fault_count=1,
            path="src/example/_helpers/example.py",
            config={"thresholds": {"max_arguments": 1}},
        ),
        NativeCustomRuleParityTestCase(
            description="FFS011 leaves top-level main ownership to FFS001 but checks methods",
            native_code="FFS011",
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
            description="FFS102 matches a public custom rule for helper parameter mutation",
            native_code="FFS102",
            source="def update(values: list[int]) -> None:\n    values.append(1)\n",
            expected_fault_count=1,
            path="src/example/_helpers/example.py",
        ),
        NativeCustomRuleParityTestCase(
            description="FFS102 native and custom guards both exclude non-helper modules",
            native_code="FFS102",
            source="def update(values: list[int]) -> None:\n    values.append(1)\n",
            expected_fault_count=0,
        ),
        NativeCustomRuleParityTestCase(
            description="FFS110 matches a public custom rule for unreturned mutations",
            native_code="FFS110",
            source=(
                "def update(left: list[int], right: list[int]) -> list[int]:\n"
                "    left.append(1)\n"
                "    right.append(2)\n"
                "    return left\n"
            ),
            expected_fault_count=1,
        ),
        NativeCustomRuleParityTestCase(
            description="FFS120 matches a public custom rule with a compact positional threshold",
            native_code="FFS120",
            source="def run(first: int, second: int) -> None:\n    return None\n",
            expected_fault_count=1,
            path="src/example/_helpers/example.py",
            config={"thresholds": {"max_positional_args": 1}},
        ),
        NativeCustomRuleParityTestCase(
            description="FFS130 matches a public custom rule for outer-state mutations",
            native_code="FFS130",
            source="CACHE: list[int] = []\n\ndef run() -> None:\n    CACHE.append(1)\n",
            expected_fault_count=1,
        ),
        NativeCustomRuleParityTestCase(
            description="FFS131 matches a public custom rule for complex comprehensions",
            native_code="FFS131",
            source="pairs = [(left, right) for left in (1, 2) for right in (3, 4)]\n",
            expected_fault_count=1,
        ),
        NativeCustomRuleParityTestCase(
            description="FFS201 matches a public custom rule for mutable dataclass models",
            native_code="FFS201",
            source=(
                "from dataclasses import dataclass\n\n@dataclass\nclass Result:\n    value: int\n"
            ),
            expected_fault_count=1,
            path="src/example/models.py",
        ),
        NativeCustomRuleParityTestCase(
            description="FFS201 native and custom guards both exclude non-model modules",
            native_code="FFS201",
            source=(
                "from dataclasses import dataclass\n\n@dataclass\nclass Result:\n    value: int\n"
            ),
            expected_fault_count=0,
            path="src/example/_helpers/example.py",
        ),
        NativeCustomRuleParityTestCase(
            description="FFR001 matches foreign declarations in models role files",
            native_code="FFR001",
            source="def build() -> None:\n    return None\n",
            expected_fault_count=1,
            path="src/example/models.py",
        ),
        NativeCustomRuleParityTestCase(
            description="FFR002 matches runtime declarations in types role files",
            native_code="FFR002",
            source="def build() -> None:\n    return None\n",
            expected_fault_count=1,
            path="src/example/types.py",
        ),
        NativeCustomRuleParityTestCase(
            description="FFR003 matches class declarations in constants role files",
            native_code="FFR003",
            source="class Config:\n    value: int\n",
            expected_fault_count=1,
            path="src/example/constants.py",
        ),
        NativeCustomRuleParityTestCase(
            description="FFR004 matches non-exception declarations in exceptions role files",
            native_code="FFR004",
            source="class Result:\n    value: int\n",
            expected_fault_count=1,
            path="src/example/exceptions.py",
        ),
        NativeCustomRuleParityTestCase(
            description="FFR101 matches model declarations outside the models role",
            native_code="FFR101",
            source=(
                "from dataclasses import dataclass\n\n"
                "@dataclass(frozen=True)\nclass Result:\n    value: int\n"
            ),
            expected_fault_count=1,
            path="src/example/_helpers/results.py",
        ),
        NativeCustomRuleParityTestCase(
            description="FFR102 matches public type declarations outside the types role",
            native_code="FFR102",
            source="from typing import Protocol\n\nclass Service(Protocol):\n    value: int\n",
            expected_fault_count=1,
            path="src/example/main/example.py",
        ),
        NativeCustomRuleParityTestCase(
            description="FFR103 matches public constants outside the constants role",
            native_code="FFR103",
            source="MAX_ITEMS: int = 3\n",
            expected_fault_count=1,
            path="src/example/_helpers/example.py",
        ),
        NativeCustomRuleParityTestCase(
            description="FFR104 matches exception declarations outside the exceptions role",
            native_code="FFR104",
            source="class ConfigError(Exception):\n    pass\n",
            expected_fault_count=1,
            path="src/example/_helpers/example.py",
        ),
        NativeCustomRuleParityTestCase(
            description="FFR201 matches generic module filenames",
            native_code="FFR201",
            source="value: int = 1\n",
            expected_fault_count=1,
            path="src/example/_helpers/misc.py",
        ),
        NativeCustomRuleParityTestCase(
            description="FFR202 matches legacy helpers module filenames",
            native_code="FFR202",
            source="value: int = 1\n",
            expected_fault_count=1,
            path="src/example/helpers.py",
        ),
        NativeCustomRuleParityTestCase(
            description="FFR203 matches monolithic classes module filenames",
            native_code="FFR203",
            source="class Service:\n    pass\n",
            expected_fault_count=1,
            path="src/example/classes.py",
        ),
        NativeCustomRuleParityTestCase(
            description="FFR205 matches public plain helper classes",
            native_code="FFR205",
            source="class Cursor:\n    pass\n",
            expected_fault_count=1,
            path="src/example/_helpers/parsing.py",
        ),
        NativeCustomRuleParityTestCase(
            description="FFR303 matches reserved role filenames beneath helpers",
            native_code="FFR303",
            source="value: int = 1\n",
            expected_fault_count=1,
            path="src/example/_helpers/models.py",
        ),
        NativeCustomRuleParityTestCase(
            description="FFR304 matches ad hoc modules directly beneath nested packages",
            native_code="FFR304",
            source="value: int = 1\n",
            expected_fault_count=1,
            path="src/example/orders/work/value.py",
        ),
        NativeCustomRuleParityTestCase(
            description="FFR305 matches arbitrary nested subpackages without role boundaries",
            native_code="FFR305",
            source="value: int = 1\n",
            expected_fault_count=1,
            path="src/example/orders/work/detail/value.py",
        ),
        NativeCustomRuleParityTestCase(
            description="FFR307 matches ad hoc direct modules in top-level domains",
            native_code="FFR307",
            source="value: int = 1\n",
            expected_fault_count=1,
            path="src/example/orders/value.py",
        ),
        NativeCustomRuleParityTestCase(
            description="FFR401 matches entry modules without one public function",
            native_code="FFR401",
            source="def _prepare() -> None:\n    return None\n",
            expected_fault_count=1,
            path="src/example/main/example.py",
        ),
        NativeCustomRuleParityTestCase(
            description="FFR402 matches nonempty nested package initializers",
            native_code="FFR402",
            source="value: int = 1\n",
            expected_fault_count=1,
            path="src/example/_helpers/__init__.py",
        ),
        NativeCustomRuleParityTestCase(
            description="FFR403 matches internal pure re-export shims",
            native_code="FFR403",
            source="from example.models import Result\n\n__all__ = ['Result']\n",
            expected_fault_count=1,
            path="src/example/result.py",
        ),
        NativeCustomRuleParityTestCase(
            description="FFR404 matches helper all declarations",
            native_code="FFR404",
            source="__all__: list[str] = []\n",
            expected_fault_count=1,
            path="src/example/_helpers/example.py",
        ),
        NativeCustomRuleParityTestCase(
            description="FFR406 matches runtime declarations on root package surfaces",
            native_code="FFR406",
            source="value: int = 1\n",
            expected_fault_count=1,
            path="src/example/__init__.py",
        ),
        NativeCustomRuleParityTestCase(
            description="FFR501 matches classes modules with multiple top-level classes",
            native_code="FFR501",
            source="class First:\n    pass\n\nclass Second:\n    pass\n",
            expected_fault_count=1,
            path="src/example/classes/service.py",
        ),
        NativeCustomRuleParityTestCase(
            description="FFR502 matches main modules beneath helpers packages",
            native_code="FFR502",
            source="def run() -> None:\n    return None\n",
            expected_fault_count=1,
            path="src/example/_helpers/main.py",
        ),
        NativeCustomRuleParityTestCase(
            description="FFR601 matches source files above their Python-resolved line limit",
            native_code="FFR601",
            source="first: int = 1\nsecond: int = 2\n",
            expected_fault_count=1,
            path="src/example/_helpers/example.py",
            config={"thresholds": {"max_file_lines": 1}},
        ),
        NativeCustomRuleParityTestCase(
            description="FFR601 preserves Python splitlines semantics for local source text",
            native_code="FFR601",
            source="# first\x0c# second\nvalue: int = 1\n",
            expected_fault_count=1,
            path="src/example/_helpers/example.py",
            config={"thresholds": {"max_file_lines": 2}},
        ),
        NativeCustomRuleParityTestCase(
            description="FFR701 matches unsupported direct-script functions",
            native_code="FFR701",
            source="def parse_args() -> object:\n    return object()\n\ndef main() -> int:\n    return 0\n",
            expected_fault_count=1,
            path="scripts/report.py",
            scope="tooling",
            scope_root="scripts",
        ),
        NativeCustomRuleParityTestCase(
            description="FFR702 matches direct scripts without imported main delegation",
            native_code="FFR702",
            source="def main() -> int:\n    return 0\n",
            expected_fault_count=1,
            path="scripts/report.py",
            scope="tooling",
            scope_root="scripts",
        ),
        NativeCustomRuleParityTestCase(
            description="FFR703 matches direct scripts above their Python-resolved line limit",
            native_code="FFR703",
            source="def main() -> int:\n    return 0\n",
            expected_fault_count=1,
            path="scripts/report.py",
            scope="tooling",
            scope_root="scripts",
            config={"thresholds": {"max_script_entrypoint_lines": 1}},
        ),
        NativeCustomRuleParityTestCase(
            description="FFR704 matches undecorated declarations in tooling rules modules",
            native_code="FFR704",
            source="def helper() -> None:\n    return None\n",
            expected_fault_count=1,
            path="scripts/example/rules/imports.py",
            scope="tooling",
            scope_root="scripts",
        ),
        NativeCustomRuleParityTestCase(
            description="FFR706 matches rule-code tooling module filenames",
            native_code="FFR706",
            source="",
            expected_fault_count=1,
            path="scripts/example/rules/fft104.py",
            scope="tooling",
            scope_root="scripts",
        ),
        NativeCustomRuleParityTestCase(
            description="FFR503 matches dynamic private declaration messages and locations",
            native_code="FFR503",
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
            description="FFR503 native and custom routing both exclude test scope",
            native_code="FFR503",
            source="def run() -> None:\n    return None\n\n_VALUE: int = 1\n",
            expected_fault_count=0,
            path="tests/unit/src/example/test_example.py",
            scope="test",
            scope_root="tests",
        ),
        NativeCustomRuleParityTestCase(
            description="FFT101 matches a public custom rule for nonempty test package modules",
            native_code="FFT101",
            source="value: int = 1\n",
            expected_fault_count=1,
            path="tests/unit/src/example/__init__.py",
            scope="test",
            scope_root="tests",
        ),
        NativeCustomRuleParityTestCase(
            description="FFT102 matches a public custom rule for relative test imports",
            native_code="FFT102",
            source="from .helpers import build_case\n",
            expected_fault_count=1,
            path="tests/unit/src/example/test_example.py",
            scope="test",
            scope_root="tests",
        ),
        NativeCustomRuleParityTestCase(
            description="FFT103 matches a public custom rule for top-level test helpers",
            native_code="FFT103",
            source="def helper() -> None:\n    return None\n",
            expected_fault_count=1,
            path="tests/unit/src/example/test_example.py",
            scope="test",
            scope_root="tests",
        ),
        NativeCustomRuleParityTestCase(
            description="FFT104 matches a public custom rule for test function conditionals",
            native_code="FFT104",
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
            description="FFT105 matches a public custom rule for private constants after tests",
            native_code="FFT105",
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
            description="FFT106 matches a public custom rule for complex test comprehensions",
            native_code="FFT106",
            source="pairs = [(left, right) for left in (1, 2) for right in (3, 4)]\n",
            expected_fault_count=1,
            path="tests/unit/src/example/test_example.py",
            scope="test",
            scope_root="tests",
        ),
        NativeCustomRuleParityTestCase(
            description="FFT201 matches a public custom rule for missing test-case descriptions",
            native_code="FFT201",
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
            description="FFT202 matches a public custom rule for missing expected fields",
            native_code="FFT202",
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
            description="FFT203 matches a public custom rule for foreign local test-type imports",
            native_code="FFT203",
            source="from tests.unit.src.other._test_types import Case\n",
            expected_fault_count=1,
            path="tests/unit/src/example/test_example.py",
            scope="test",
            scope_root="tests",
        ),
        NativeCustomRuleParityTestCase(
            description="FFT301 matches a public custom rule for test module filenames",
            native_code="FFT301",
            source="",
            expected_fault_count=1,
            path="tests/unit/src/example/example.py",
            scope="test",
            scope_root="tests",
        ),
        NativeCustomRuleParityTestCase(
            description="FFT302 matches a public custom rule for test function names",
            native_code="FFT302",
            source="def test_bad_name() -> None:\n    return None\n",
            expected_fault_count=1,
            path="tests/unit/src/example/test_example.py",
            scope="test",
            scope_root="tests",
        ),
        NativeCustomRuleParityTestCase(
            description="FFT401 matches a public custom rule for missing parameterization",
            native_code="FFT401",
            source=(
                "def test_given_value_when_checking_then_matches() -> None:\n    return None\n"
            ),
            expected_fault_count=1,
            path="tests/unit/src/example/test_example.py",
            scope="test",
            scope_root="tests",
        ),
        NativeCustomRuleParityTestCase(
            description="FFT402 matches a public custom rule for missing test_case parameters",
            native_code="FFT402",
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
            description="FFT404 matches a public custom rule for missing expected-field references",
            native_code="FFT404",
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
            description="FFT405 matches a public custom rule for missing parametrize values",
            native_code="FFT405",
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
            description="FFT406 matches a public custom rule for wrong parametrize parameter names",
            native_code="FFT406",
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
            description="FFT407 matches a public custom rule for missing parametrize ids",
            native_code="FFT407",
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
            description="FFT408 matches a public custom rule for indirect parametrize values",
            native_code="FFT408",
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
            description="FFT411 matches a public custom rule for empty parametrize values",
            native_code="FFT411",
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
            description="FFT412 matches a public custom rule for dictionary test cases",
            native_code="FFT412",
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
            description="FFT414 matches a public custom rule for non-description ids",
            native_code="FFT414",
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
            description="FFL103 matches a public custom rule for bare package imports",
            native_code="FFL103",
            source="from example import PublicModel\nimport example as public_api\n",
            expected_fault_count=2,
        ),
        NativeCustomRuleParityTestCase(
            description="FFL301 matches a public custom rule for configured tooling imports",
            native_code="FFL301",
            source="from scripts.release import publish\nimport scripts.formatting as formatting\n",
            expected_fault_count=2,
            files=(
                RuleFile(path="scripts/release.py", source="def publish() -> None:\n    pass\n"),
            ),
        ),
        NativeCustomRuleParityTestCase(
            description="FFT102 native and custom routing both exclude runtime scope",
            native_code="FFT102",
            source="from .helpers import build_case\n",
            expected_fault_count=0,
        ),
        NativeCustomRuleParityTestCase(
            description="FFS101 matches public project function resolution",
            native_code="FFS101",
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
            description="FFL101 matches public sibling package observations",
            native_code="FFL101",
            source="from example.domain.beta._helpers import load\n",
            expected_fault_count=1,
            path="src/example/domain/alpha/main/run.py",
        ),
        NativeCustomRuleParityTestCase(
            description="FFL102 matches public cross-domain package observations",
            native_code="FFL102",
            source="from example.other._helpers import load\n",
            expected_fault_count=1,
            path="src/example/domain/main/run.py",
        ),
        NativeCustomRuleParityTestCase(
            description="FFL104 matches public module existence observations",
            native_code="FFL104",
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
            description="FFR204 matches public namespace package anchors",
            native_code="FFR204",
            source="",
            expected_fault_count=1,
            path="src/example/shared/__init__.py",
        ),
        NativeCustomRuleParityTestCase(
            description="FFL105 matches public project import graph observations",
            native_code="FFL105",
            source="def run() -> None:\n    pass\n",
            expected_fault_count=1,
            path="src/example/domain/main/run.py",
        ),
        NativeCustomRuleParityTestCase(
            description="FFR301 matches public helpers package observations",
            native_code="FFR301",
            source="",
            expected_fault_count=0,
            path="src/example/domain/_helpers/__init__.py",
        ),
        NativeCustomRuleParityTestCase(
            description="FFR302 matches public main package observations",
            native_code="FFR302",
            source="",
            expected_fault_count=0,
            path="src/example/domain/main/__init__.py",
        ),
        NativeCustomRuleParityTestCase(
            description="FFR306 matches public domain shape observations",
            native_code="FFR306",
            source="",
            expected_fault_count=0,
            path="src/example/domain/models.py",
        ),
        NativeCustomRuleParityTestCase(
            description="FFR308 matches public scope prefix observations",
            native_code="FFR308",
            source="",
            expected_fault_count=0,
            path="src/example/domain/models.py",
        ),
        NativeCustomRuleParityTestCase(
            description="FFR309 matches public leaf main observations",
            native_code="FFR309",
            source="def run() -> None:\n    pass\n",
            expected_fault_count=0,
            path="src/example/domain/main/run.py",
        ),
        NativeCustomRuleParityTestCase(
            description="FFR405 matches public sibling directory observations",
            native_code="FFR405",
            source="def run() -> None:\n    pass\n",
            expected_fault_count=1,
            path="src/example/main/run.py",
            files=(RuleFile(path="src/example/main/run/__init__.py", source=""),),
        ),
        NativeCustomRuleParityTestCase(
            description="FFR705 matches public tooling package anchors",
            native_code="FFR705",
            source="",
            expected_fault_count=1,
            path="scripts/tool/misc/__init__.py",
            scope="tooling",
            scope_root="scripts",
        ),
        NativeCustomRuleParityTestCase(
            description="FFR707 native and public routing agree without registrations",
            native_code="FFR707",
            source="",
            expected_fault_count=0,
        ),
        NativeCustomRuleParityTestCase(
            description="FFT001 matches public shallow test layout decisions",
            native_code="FFT001",
            source="",
            expected_fault_count=1,
            path="tests/test_example.py",
            scope="test",
            scope_root="tests",
        ),
        NativeCustomRuleParityTestCase(
            description="FFT002 matches public test scope decisions",
            native_code="FFT002",
            source="",
            expected_fault_count=1,
            path="tests/slow/src/example/test_example.py",
            scope="test",
            scope_root="tests",
        ),
        NativeCustomRuleParityTestCase(
            description="FFT003 matches public mirror root decisions",
            native_code="FFT003",
            source="",
            expected_fault_count=1,
            path="tests/unit/docs/example/test_example.py",
            scope="test",
            scope_root="tests",
        ),
        NativeCustomRuleParityTestCase(
            description="FFT004 matches public runtime mirror depth decisions",
            native_code="FFT004",
            source="",
            expected_fault_count=1,
            path="tests/unit/src/example/test_example.py",
            scope="test",
            scope_root="tests",
            files=(RuleFile(path="src/example/__init__.py", source=""),),
        ),
        NativeCustomRuleParityTestCase(
            description="FFT005 matches public source package decisions",
            native_code="FFT005",
            source="",
            expected_fault_count=1,
            path="tests/unit/src/other/core/test_example.py",
            scope="test",
            scope_root="tests",
            files=(RuleFile(path="src/example/__init__.py", source=""),),
        ),
        NativeCustomRuleParityTestCase(
            description="FFT006 matches public runtime area observations",
            native_code="FFT006",
            source="",
            expected_fault_count=1,
            path="tests/unit/src/example/missing/test_example.py",
            scope="test",
            scope_root="tests",
            files=(RuleFile(path="src/example/__init__.py", source=""),),
        ),
        NativeCustomRuleParityTestCase(
            description="FFT007 matches public tooling mirror depth decisions",
            native_code="FFT007",
            source="",
            expected_fault_count=1,
            path="tests/unit/scripts/test_example.py",
            scope="test",
            scope_root="tests",
            files=(RuleFile(path="scripts/tool.py", source=""),),
        ),
        NativeCustomRuleParityTestCase(
            description="FFT008 matches public tooling area observations",
            native_code="FFT008",
            source="",
            expected_fault_count=1,
            path="tests/unit/scripts/missing/test_example.py",
            scope="test",
            scope_root="tests",
            files=(RuleFile(path="scripts/tool.py", source=""),),
        ),
        NativeCustomRuleParityTestCase(
            description="FFT204 matches public sibling file observations",
            native_code="FFT204",
            source="",
            expected_fault_count=1,
            path="tests/unit/src/example/test_example.py",
            scope="test",
            scope_root="tests",
        ),
        NativeCustomRuleParityTestCase(
            description="FFT403 matches public sibling dataclass facts",
            native_code="FFT403",
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
            description="FFT413 matches public local constructor facts",
            native_code="FFT413",
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
            description="FFT106 native and custom routing both exclude runtime scope",
            native_code="FFT106",
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
