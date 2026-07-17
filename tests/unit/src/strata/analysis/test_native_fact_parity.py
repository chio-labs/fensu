"""Backend parity for native fact families over targeted syntax shapes."""

from pathlib import Path
from typing import Any

import pytest

from strata.analysis.constants import NATIVE_FACT_MODULE_NAME

strata_facts: Any = pytest.importorskip(NATIVE_FACT_MODULE_NAME)

from tests.unit.src.strata.analysis._test_types import NativeFactParityTestCase  # noqa: E402
from tests.unit.src.strata.analysis.helpers import fact_family_divergences  # noqa: E402


@pytest.mark.parametrize(
    "test_case",
    [
        NativeFactParityTestCase(
            description="comment columns after multibyte text and trailing spaces",
            source='x = "caf\u00e9"  # note \u2713  \n# lead\n\t# tabbed\n',
            expected_divergent=(),
        ),
        NativeFactParityTestCase(
            description="global and nonlocal outer-state mutations",
            source=(
                "g = 0\n"
                "def f():\n"
                "    global g\n"
                "    g = 5\n"
                "def outer():\n"
                "    x = 0\n"
                "    def inner():\n"
                "        nonlocal x\n"
                "        x += 1\n"
            ),
            expected_divergent=(),
        ),
        NativeFactParityTestCase(
            description="module and closure container mutations with shadowing",
            source=(
                "cache = {}\n"
                "items = []\n"
                "def f():\n"
                "    cache['k'] = 1\n"
                "    items.append(2)\n"
                "def g():\n"
                "    cache = {}\n"
                "    cache['k'] = 1\n"
                "def h():\n"
                "    [cache.pop(k) for cache in ([],)]\n"
            ),
            expected_divergent=(),
        ),
        NativeFactParityTestCase(
            description="shadowed and resolvable discarded project calls",
            source=(
                "import mod\n"
                "import pkg.sub as p\n"
                "from lib import work\n"
                "def f(work):\n"
                "    work()\n"
                "def g():\n"
                "    work()\n"
                "    mod.run()\n"
                "    p.go()\n"
                "def h():\n"
                "    work = object\n"
                "    work()\n"
            ),
            expected_divergent=(),
        ),
        NativeFactParityTestCase(
            description="string and parenthesized return annotations with yields",
            source=(
                "from typing import Iterator\n"
                "def a() -> 'Iterator[int]':\n"
                "    yield 1\n"
                "def b() -> (\n"
                "    int\n"
                "    | None\n"
                "):\n"
                "    return 1\n"
                "def c() -> 'None':\n"
                "    return None\n"
                "def d() -> tuple[int, ...]:\n"
                "    return (1,)\n"
            ),
            expected_divergent=(),
        ),
        NativeFactParityTestCase(
            description="elif chains and ternaries inside functions",
            source=(
                "def f(a: int) -> int:\n"
                "    if a:\n"
                "        return 1\n"
                "    elif a > 5:\n"
                "        return 2\n"
                "    elif a > 9:\n"
                "        return 3\n"
                "    else:\n"
                "        return 4 if a else 5\n"
            ),
            expected_divergent=(),
        ),
        NativeFactParityTestCase(
            description="string and magic numeric comparison decisions",
            source=(
                "import sys\n"
                "def f(v: object) -> bool:\n"
                "    if v == 'mode':\n"
                "        return True\n"
                "    if v in ('a', 'b') or v in frozenset({'c'}):\n"
                "        return True\n"
                "    if v == 42 or v == -5 or v == 2.5 or v == 1:\n"
                "        return True\n"
                "    return sys.maxsize > 100\n"
                "if __name__ == '__main__':\n"
                "    f('x')\n"
            ),
            expected_divergent=(),
        ),
        NativeFactParityTestCase(
            description="raw raises assertions and swallowed probes",
            source=(
                "def f() -> None:\n"
                "    assert True\n"
                "    try:\n"
                "        raise ValueError('x')\n"
                "    except Exception:\n"
                "        return None\n"
                "    try:\n"
                "        raise mod.ValueError('x')\n"
                "    except Exception as error:\n"
                "        raise\n"
            ),
            expected_divergent=(),
        ),
        NativeFactParityTestCase(
            description="dataclass frozen and shape metadata",
            source=(
                "from dataclasses import dataclass\n"
                "import attr\n"
                "@dataclass(frozen=True, slots=True)\n"
                "class A:\n"
                "    x: int\n"
                "    y: str = 'a'\n"
                "@dataclass\n"
                "class B:\n"
                "    z: int\n"
                "@attr.dataclass(frozen=False)\n"
                "class C:\n"
                "    w: int\n"
            ),
            expected_divergent=(),
        ),
        NativeFactParityTestCase(
            description="multiline docstrings including escaped newlines",
            source=(
                '"""Module\ndocstring."""\n'
                "def f() -> None:\n"
                "    'single\\nline escape'\n"
                "class C:\n"
                '    """One line."""\n'
            ),
            expected_divergent=(),
        ),
        NativeFactParityTestCase(
            description="test module shape with case lists and private constants",
            source=(
                '"""Docstring."""\n'
                "import pytest\n"
                "TEST_CASES = [1]\n"
                "EXTRA_TEST_CASES = [2]\n"
                "def helper() -> None:\n"
                "    pass\n"
                "def test_given_when_then() -> None:\n"
                "    assert TEST_CASES\n"
                "_PRIVATE = 3\n"
            ),
            expected_divergent=(),
        ),
        NativeFactParityTestCase(
            description="relative imports dotted imports and private attribute references",
            source=(
                "from . import sibling\n"
                "from ..pkg import name as alias\n"
                "import one.two.three\n"
                "import one.two as ot\n"
                "value = ot._Hidden()\n"
                "other = sibling.mod._Deep._Inner\n"
            ),
            expected_divergent=(),
        ),
        NativeFactParityTestCase(
            description="parameter mutations with setter dunder and returns",
            source=(
                "class C:\n"
                "    @value.setter\n"
                "    def value(self, item: dict) -> None:\n"
                "        item['k'] = 1\n"
                "    def __iadd__(self, other: list) -> list:\n"
                "        other.append(1)\n"
                "        return other\n"
                "def f(data: dict, keys: list) -> dict:\n"
                "    data['k'] = 2\n"
                "    keys.extend([1])\n"
                "    return data\n"
            ),
            expected_divergent=(),
        ),
        NativeFactParityTestCase(
            description="rule authoring owners references and exact literal values",
            source=(
                "@registry.wrap()\n"
                "class Caf\u00e9(pkg.Base[T]):\n"
                "    def outer(self, items):\n"
                "        left, *rest = source.value\n"
                "        while ready:\n"
                "            def inner():\n"
                "                service.call(\n"
                "                    'a' 'b', b'\\x00' b'\\xff',\n"
                "                    0x100000000000000000000000000000001,\n"
                "                    1.25, 3.5j, False, None, ...\n"
                "                )\n"
                "        items.append(1)\n"
                "        items.append(2)\n"
                "        return items\n"
                "if pkg.value == compute() < rows[index] != factory().attr:\n"
                "    pass\n"
            ),
            expected_divergent=(),
        ),
        NativeFactParityTestCase(
            description="escaped lone surrogate literal retains exact CPython value",
            source="f('\\ud800')\n",
            expected_divergent=(),
        ),
        NativeFactParityTestCase(
            description="variadic parameter mutations retain filterable parameter kinds",
            source=("def update(*args, **kwargs):\n    args.append(1)\n    kwargs.update({})\n"),
            expected_divergent=(),
        ),
        NativeFactParityTestCase(
            description="fstring interpolations with format specs and nesting",
            source=(
                "w = 10\n"
                "def f(x: float, q: str) -> str:\n"
                "    lead = f'{x:>{w}.2f} end'\n"
                "    joined = 'a' f'b{q!r:,}c' 'd'\n"
                "    return lead + joined\n"
            ),
            expected_divergent=(),
        ),
        NativeFactParityTestCase(
            description="module declarations with guards aliases and reexports",
            source=(
                '"""Docstring."""\n'
                "from __future__ import annotations\n"
                "from typing import TYPE_CHECKING, NewType, TypeAlias\n"
                "if TYPE_CHECKING:\n"
                "    import late\n"
                "Alias: TypeAlias = int\n"
                "Ident = NewType('Ident', str)\n"
                "type Modern = list[int]\n"
                "__all__ = ['Alias']\n"
                "if __name__ == '__main__':\n"
                "    print('run')\n"
            ),
            expected_divergent=(),
        ),
        NativeFactParityTestCase(
            description="annotations traversal with enums receivers and locals",
            source=(
                "from enum import StrEnum\n"
                "class Color(StrEnum):\n"
                "    RED = 'red'\n"
                "class Holder:\n"
                "    attr = 1\n"
                "    def method(self, given, *extra, named=2, **rest):\n"
                "        first = 1\n"
                "        first = 2\n"
                "        second: int = 3\n"
                "        _ = 4\n"
                "        third = f'{given}'\n"
                "module_var = 5\n"
                "__version__ = '1.0'\n"
            ),
            expected_divergent=(),
        ),
        NativeFactParityTestCase(
            description="complex and filtered comprehensions inside definitions",
            source=(
                "def f(rows: list) -> list:\n"
                "    flat = [x for row in rows for x in row]\n"
                "    nested = [[y for y in row] for row in rows]\n"
                "    filtered = [x for x in rows if x]\n"
                "    gen = sum(x for x in rows if x)\n"
                "    return flat + nested + filtered + [gen]\n"
            ),
            expected_divergent=(),
        ),
        NativeFactParityTestCase(
            description="harness calls with duplicate single and literal case forms",
            source=(
                "import pytest\n"
                "import strata\n"
                "from strata import RuleCase, evaluate_rule\n"
                "CASES = [RuleCase(), RuleCase()]\n"
                "@pytest.mark.parametrize('test_case', CASES)\n"
                "@pytest.mark.parametrize('test_case', [RuleCase()])\n"
                "def test_given_duplicate_dimensions_when_evaluating_then_unknown(test_case):\n"
                "    evaluate_rule(rule=None, test_case=test_case)\n"
                "@pytest.mark.parametrize('test_case', CASES)\n"
                "def test_given_named_cases_when_evaluating_then_counted(test_case):\n"
                "    strata.evaluate_rule(rule=strata.rules.demo, test_case=test_case)\n"
                "def test_given_literal_case_when_evaluating_then_literal():\n"
                "    evaluate_rule(rule=None, test_case=RuleCase(kind='x'))\n"
                "def test_given_shadowed_harness_when_evaluating_then_skipped():\n"
                "    evaluate_rule = object\n"
                "    evaluate_rule(rule=None, test_case=RuleCase())\n"
            ),
            expected_divergent=(),
        ),
        NativeFactParityTestCase(
            description="decorated async functions and lambda scopes",
            source=(
                "import functools\n"
                "@functools.cache\n"
                "async def fetch(url: str) -> bytes:\n"
                "    async with session() as s:\n"
                "        return await s.get(url)\n"
                "handler = lambda event: event.name\n"
                "def sync_after() -> None:\n"
                "    return None\n"
            ),
            expected_divergent=(),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_targeted_source_when_extracting_families_then_backends_agree(
    test_case: NativeFactParityTestCase,
    tmp_path: Path,
) -> None:
    divergent: tuple[str, ...] = fact_family_divergences(
        path=tmp_path / "module.py",
        source=test_case.source,
    )

    assert divergent == test_case.expected_divergent
