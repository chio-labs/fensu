"""Tests for hygiene rules."""

from __future__ import annotations

from pathlib import Path

import pytest

from fensu.evaluation.models import EvaluationResult
from tests.unit.src.fensu.rules.hygiene.main._test_types import HygieneRuleTestCase
from tests.unit.src.fensu.rules.hygiene.main.helpers import evaluate_hygiene_test_case


@pytest.mark.parametrize(
    "test_case",
    [
        HygieneRuleTestCase(
            description="multiline module docstring is flagged",
            rule_code="FFH001",
            source='"""Summary.\n\nDetails.\n"""\nvalue: int = 1\n',
            expected_codes=("FFH001",),
            expected_lines=(1,),
        ),
        HygieneRuleTestCase(
            description="single-line function docstring is allowed",
            rule_code="FFH001",
            source='def run() -> None:\n    """Run the task."""\n    return None\n',
            expected_codes=(),
            expected_lines=(),
        ),
        HygieneRuleTestCase(
            description="multiline class docstring is flagged",
            rule_code="FFH001",
            source='class Service:\n    """Summary.\n\n    Details.\n    """\n',
            expected_codes=("FFH001",),
            expected_lines=(2,),
        ),
        HygieneRuleTestCase(
            description="multiline async function docstring is flagged",
            rule_code="FFH001",
            source='async def run() -> None:\n    """Summary.\n\n    Details.\n    """\n',
            expected_codes=("FFH001",),
            expected_lines=(2,),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_docstrings_when_checking_hygiene_then_flags_only_multiline_docstrings(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: HygieneRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_hygiene_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        HygieneRuleTestCase(
            description="standalone explanatory comment is flagged",
            rule_code="FFH002",
            source="value: int = 1\n# explain the branch\nother: int = 2\n",
            expected_codes=("FFH002",),
            expected_lines=(2,),
        ),
        HygieneRuleTestCase(
            description="allowed tooling prefixes are ignored",
            rule_code="FFH002",
            source=(
                "#!/usr/bin/env python\n"
                "# -*- coding: utf-8 -*-\n"
                "# coding: utf-8\n"
                "# noqa: E501\n"
                "value: int = 1  # type: ignore[assignment]\n"
                "# pyright: ignore[reportUnknownVariableType]\n"
                "# pylint: disable=missing-docstring\n"
                "# pragma: no cover\n"
            ),
            expected_codes=(),
            expected_lines=(),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_comments_when_checking_hygiene_then_flags_only_disallowed_comments(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: HygieneRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_hygiene_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        HygieneRuleTestCase(
            description="raw builtin exception raise is flagged",
            rule_code="FFH003",
            source="def run() -> None:\n    raise ValueError('bad')\n",
            expected_codes=("FFH003",),
            expected_lines=(2,),
        ),
        HygieneRuleTestCase(
            description="raw builtin exception class raise is flagged",
            rule_code="FFH003",
            source="def run() -> None:\n    raise ValueError\n",
            expected_codes=("FFH003",),
            expected_lines=(2,),
        ),
        HygieneRuleTestCase(
            description="structured exception raise is allowed",
            rule_code="FFH003",
            source=(
                "class ConfigError(Exception):\n"
                "    pass\n\n"
                "def run() -> None:\n"
                "    raise ConfigError('bad')\n"
            ),
            expected_codes=(),
            expected_lines=(),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_raises_when_checking_hygiene_then_flags_only_raw_builtin_exceptions(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: HygieneRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_hygiene_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        HygieneRuleTestCase(
            description="assert statement is flagged",
            rule_code="FFH004",
            source="def run(value: int) -> None:\n    assert value > 0\n",
            expected_codes=("FFH004",),
            expected_lines=(2,),
        ),
        HygieneRuleTestCase(
            description="explicit guard without assert is allowed",
            rule_code="FFH004",
            source="def run(value: int) -> None:\n    if value <= 0:\n        return None\n",
            expected_codes=(),
            expected_lines=(),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_asserts_when_checking_hygiene_then_flags_assert_statements(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: HygieneRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_hygiene_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        HygieneRuleTestCase(
            description="bare broad exception returning None is flagged",
            rule_code="FFH005",
            source=(
                "def exists() -> bool | None:\n"
                "    try:\n"
                "        return bool(object())\n"
                "    except Exception:\n"
                "        return None\n"
            ),
            expected_codes=("FFH005",),
            expected_lines=(4,),
        ),
        HygieneRuleTestCase(
            description="bare broad exception continuing loop is flagged",
            rule_code="FFH005",
            source=(
                "def run(items: list[int]) -> None:\n"
                "    for item in items:\n"
                "        try:\n"
                "            int(item)\n"
                "        except Exception:\n"
                "            continue\n"
            ),
            expected_codes=("FFH005",),
            expected_lines=(5,),
        ),
        HygieneRuleTestCase(
            description="bare broad exception returning False is flagged",
            rule_code="FFH005",
            source=(
                "def exists() -> bool:\n"
                "    try:\n"
                "        return bool(object())\n"
                "    except Exception:\n"
                "        return False\n"
            ),
            expected_codes=("FFH005",),
            expected_lines=(4,),
        ),
        HygieneRuleTestCase(
            description="bare broad exception returning empty dict is flagged",
            rule_code="FFH005",
            source=(
                "def load() -> dict[str, str]:\n"
                "    try:\n"
                "        return {'value': 'ok'}\n"
                "    except Exception:\n"
                "        return {}\n"
            ),
            expected_codes=("FFH005",),
            expected_lines=(4,),
        ),
        HygieneRuleTestCase(
            description="bare broad exception returning empty tuple is flagged",
            rule_code="FFH005",
            source=(
                "def load() -> tuple[str, ...]:\n"
                "    try:\n"
                "        return ('ok',)\n"
                "    except Exception:\n"
                "        return ()\n"
            ),
            expected_codes=("FFH005",),
            expected_lines=(4,),
        ),
        HygieneRuleTestCase(
            description="named broad exception with handling is allowed",
            rule_code="FFH005",
            source=(
                "def exists() -> bool:\n"
                "    try:\n"
                "        return bool(object())\n"
                "    except Exception as exc:\n"
                "        raise RuntimeError(str(exc))\n"
            ),
            expected_codes=(),
            expected_lines=(),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_exception_handlers_when_checking_hygiene_then_flags_only_probe_swallows(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: HygieneRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_hygiene_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        HygieneRuleTestCase(
            description="multi-generator comprehension in tooling is flagged",
            rule_code="FFH006",
            source="pairs: list[tuple[int, int]] = [(left, right) for left in (1, 2) for right in (3, 4)]\n",
            expected_codes=("FFH006",),
            expected_lines=(1,),
            relative_path="scripts/check.py",
            roots=(),
            tooling=("scripts",),
        ),
        HygieneRuleTestCase(
            description="product comprehension is owned by shape counterpart",
            rule_code="FFH006",
            source="pairs: list[tuple[int, int]] = [(left, right) for left in (1, 2) for right in (3, 4)]\n",
            expected_codes=(),
            expected_lines=(),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_comprehensions_when_checking_tooling_then_applies_only_to_tooling_scope(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: HygieneRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_hygiene_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        HygieneRuleTestCase(
            description="string equality decision is flagged",
            rule_code="FFH007",
            source="def ready(status: str) -> bool:\n    return status == 'ready'\n",
            expected_codes=("FFH007",),
            expected_lines=(2,),
        ),
        HygieneRuleTestCase(
            description="string membership values are each flagged",
            rule_code="FFH007",
            source="def ready(status: str) -> bool:\n    return status in {'ready', 'done'}\n",
            expected_codes=("FFH007", "FFH007"),
            expected_lines=(2, 2),
        ),
        HygieneRuleTestCase(
            description="frozenset string membership value is flagged",
            rule_code="FFH007",
            source="def ready(status: str) -> bool:\n    return status in frozenset({'ready'})\n",
            expected_codes=("FFH007",),
            expected_lines=(2,),
        ),
        HygieneRuleTestCase(
            description="named string decision is allowed",
            rule_code="FFH007",
            source="READY: str = 'ready'\n\ndef ready(status: str) -> bool:\n    return status == READY\n",
            expected_codes=(),
            expected_lines=(),
        ),
        HygieneRuleTestCase(
            description="string outside comparison is allowed",
            rule_code="FFH007",
            source="def message() -> str:\n    return 'ready'\n",
            expected_codes=(),
            expected_lines=(),
        ),
        HygieneRuleTestCase(
            description="canonical main execution guard is allowed",
            rule_code="FFH007",
            source="if __name__ == '__main__':\n    main()\n",
            expected_codes=(),
            expected_lines=(),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_string_literals_when_checking_decisions_then_requires_named_values(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: HygieneRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_hygiene_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        HygieneRuleTestCase(
            description="numeric threshold comparison is flagged",
            rule_code="FFH008",
            source="def enough(count: int) -> bool:\n    return count >= 3\n",
            expected_codes=("FFH008",),
            expected_lines=(2,),
        ),
        HygieneRuleTestCase(
            description="chained numeric bounds are each flagged",
            rule_code="FFH008",
            source="def valid(value: int) -> bool:\n    return 5 < value <= 10\n",
            expected_codes=("FFH008", "FFH008"),
            expected_lines=(2, 2),
        ),
        HygieneRuleTestCase(
            description="numeric membership values are each flagged",
            rule_code="FFH008",
            source="def valid(value: int) -> bool:\n    return value in {2, 3}\n",
            expected_codes=("FFH008", "FFH008"),
            expected_lines=(2, 2),
        ),
        HygieneRuleTestCase(
            description="canonical numeric sentinels are allowed",
            rule_code="FFH008",
            source=(
                "def valid(value: int) -> bool:\n"
                "    return value >= -1 and value != 0 and value <= 1\n"
            ),
            expected_codes=(),
            expected_lines=(),
        ),
        HygieneRuleTestCase(
            description="named numeric threshold is allowed",
            rule_code="FFH008",
            source="LIMIT: int = 3\n\ndef enough(count: int) -> bool:\n    return count >= LIMIT\n",
            expected_codes=(),
            expected_lines=(),
        ),
        HygieneRuleTestCase(
            description="numeric literal outside comparison is allowed",
            rule_code="FFH008",
            source="def increment(value: int) -> int:\n    return value + 3\n",
            expected_codes=(),
            expected_lines=(),
        ),
        HygieneRuleTestCase(
            description="boolean comparison is not a numeric decision",
            rule_code="FFH008",
            source="def enabled(value: bool) -> bool:\n    return value is True\n",
            expected_codes=(),
            expected_lines=(),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_numeric_literals_when_checking_comparisons_then_requires_named_thresholds(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: HygieneRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_hygiene_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        HygieneRuleTestCase(
            description="runtime module standalone call is flagged",
            rule_code="FFH009",
            source="register_plugins()\n",
            expected_codes=("FFH009",),
            expected_lines=(1,),
            relative_path="src/pkg/domain/core/_helpers/startup.py",
        ),
        HygieneRuleTestCase(
            description="tooling module standalone call is flagged",
            rule_code="FFH009",
            source="register_plugins()\n",
            expected_codes=("FFH009",),
            expected_lines=(1,),
            relative_path="scripts/_helpers/startup.py",
            tooling=("scripts",),
        ),
        HygieneRuleTestCase(
            description="test module standalone call remains outside hygiene scope",
            rule_code="FFH009",
            source="register_plugins()\n",
            expected_codes=(),
            expected_lines=(),
            relative_path="tests/unit/test_startup.py",
            tests=("tests",),
        ),
        HygieneRuleTestCase(
            description="assigned constructor call is allowed",
            rule_code="FFH009",
            source="LOGGER: object = get_logger()\n",
            expected_codes=(),
            expected_lines=(),
        ),
        HygieneRuleTestCase(
            description="call inside function body is allowed",
            rule_code="FFH009",
            source="def start() -> None:\n    register_plugins()\n",
            expected_codes=(),
            expected_lines=(),
        ),
        HygieneRuleTestCase(
            description="standalone call in class body is flagged",
            rule_code="FFH009",
            source="class Service:\n    register_plugins()\n",
            expected_codes=("FFH009",),
            expected_lines=(2,),
        ),
        HygieneRuleTestCase(
            description="conditional import-time call is flagged",
            rule_code="FFH009",
            source="if enabled:\n    register_plugins()\n",
            expected_codes=("FFH009",),
            expected_lines=(2,),
        ),
        HygieneRuleTestCase(
            description="type-checking guarded call is not executed at import",
            rule_code="FFH009",
            source="if TYPE_CHECKING:\n    register_type_adapter()\n",
            expected_codes=(),
            expected_lines=(),
        ),
        HygieneRuleTestCase(
            description="main-guarded call is not executed during import",
            rule_code="FFH009",
            source="if __name__ == '__main__':\n    main()\n",
            expected_codes=(),
            expected_lines=(),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_import_time_calls_when_checking_hygiene_then_preserves_effective_scope(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: HygieneRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_hygiene_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines
