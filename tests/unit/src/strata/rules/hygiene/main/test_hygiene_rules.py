"""Tests for hygiene rules."""

from __future__ import annotations

from pathlib import Path

import pytest

from strata.evaluation.core.models import EvaluationResult
from tests.unit.src.strata.rules.hygiene.main._test_types import HygieneRuleTestCase
from tests.unit.src.strata.rules.hygiene.main.helpers import evaluate_hygiene_test_case


@pytest.mark.parametrize(
    "test_case",
    [
        HygieneRuleTestCase(
            description="multiline module docstring is flagged",
            rule_code="SFX001",
            source='"""Summary.\n\nDetails.\n"""\nvalue: int = 1\n',
            expected_codes=("SFX001",),
            expected_lines=(1,),
        ),
        HygieneRuleTestCase(
            description="single-line function docstring is allowed",
            rule_code="SFX001",
            source='def run() -> None:\n    """Run the task."""\n    return None\n',
            expected_codes=(),
            expected_lines=(),
        ),
        HygieneRuleTestCase(
            description="multiline class docstring is flagged",
            rule_code="SFX001",
            source='class Service:\n    """Summary.\n\n    Details.\n    """\n',
            expected_codes=("SFX001",),
            expected_lines=(2,),
        ),
        HygieneRuleTestCase(
            description="multiline async function docstring is flagged",
            rule_code="SFX001",
            source='async def run() -> None:\n    """Summary.\n\n    Details.\n    """\n',
            expected_codes=("SFX001",),
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
            rule_code="SFX002",
            source="value: int = 1\n# explain the branch\nother: int = 2\n",
            expected_codes=("SFX002",),
            expected_lines=(2,),
        ),
        HygieneRuleTestCase(
            description="allowed tooling prefixes are ignored",
            rule_code="SFX002",
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
            rule_code="SFX003",
            source="def run() -> None:\n    raise ValueError('bad')\n",
            expected_codes=("SFX003",),
            expected_lines=(2,),
        ),
        HygieneRuleTestCase(
            description="raw builtin exception class raise is flagged",
            rule_code="SFX003",
            source="def run() -> None:\n    raise ValueError\n",
            expected_codes=("SFX003",),
            expected_lines=(2,),
        ),
        HygieneRuleTestCase(
            description="structured exception raise is allowed",
            rule_code="SFX003",
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
            rule_code="SFX004",
            source="def run(value: int) -> None:\n    assert value > 0\n",
            expected_codes=("SFX004",),
            expected_lines=(2,),
        ),
        HygieneRuleTestCase(
            description="explicit guard without assert is allowed",
            rule_code="SFX004",
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
            rule_code="SFX005",
            source=(
                "def exists() -> bool | None:\n"
                "    try:\n"
                "        return bool(object())\n"
                "    except Exception:\n"
                "        return None\n"
            ),
            expected_codes=("SFX005",),
            expected_lines=(4,),
        ),
        HygieneRuleTestCase(
            description="bare broad exception continuing loop is flagged",
            rule_code="SFX005",
            source=(
                "def run(items: list[int]) -> None:\n"
                "    for item in items:\n"
                "        try:\n"
                "            int(item)\n"
                "        except Exception:\n"
                "            continue\n"
            ),
            expected_codes=("SFX005",),
            expected_lines=(5,),
        ),
        HygieneRuleTestCase(
            description="bare broad exception returning False is flagged",
            rule_code="SFX005",
            source=(
                "def exists() -> bool:\n"
                "    try:\n"
                "        return bool(object())\n"
                "    except Exception:\n"
                "        return False\n"
            ),
            expected_codes=("SFX005",),
            expected_lines=(4,),
        ),
        HygieneRuleTestCase(
            description="bare broad exception returning empty dict is flagged",
            rule_code="SFX005",
            source=(
                "def load() -> dict[str, str]:\n"
                "    try:\n"
                "        return {'value': 'ok'}\n"
                "    except Exception:\n"
                "        return {}\n"
            ),
            expected_codes=("SFX005",),
            expected_lines=(4,),
        ),
        HygieneRuleTestCase(
            description="bare broad exception returning empty tuple is flagged",
            rule_code="SFX005",
            source=(
                "def load() -> tuple[str, ...]:\n"
                "    try:\n"
                "        return ('ok',)\n"
                "    except Exception:\n"
                "        return ()\n"
            ),
            expected_codes=("SFX005",),
            expected_lines=(4,),
        ),
        HygieneRuleTestCase(
            description="named broad exception with handling is allowed",
            rule_code="SFX005",
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
            rule_code="SFX006",
            source="pairs: list[tuple[int, int]] = [(left, right) for left in (1, 2) for right in (3, 4)]\n",
            expected_codes=("SFX006",),
            expected_lines=(1,),
            relative_path="scripts/check.py",
            roots=(),
            tooling=("scripts",),
        ),
        HygieneRuleTestCase(
            description="product comprehension is owned by shape counterpart",
            rule_code="SFX006",
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
