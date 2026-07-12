"""Tests for naming contract rules."""

from __future__ import annotations

from pathlib import Path

import pytest

from strata.evaluation.models import EvaluationResult
from tests.unit.src.strata.rules.naming.main._test_types import SfnRuleTestCase
from tests.unit.src.strata.rules.naming.main.helpers import evaluate_naming_test_case


@pytest.mark.parametrize(
    "test_case",
    [
        SfnRuleTestCase(
            description="validator returning value is flagged",
            source="def validate_config() -> bool:\n    return True\n",
            expected_codes=("SFN001",),
            expected_lines=(2,),
        ),
        SfnRuleTestCase(
            description="validator returning None is allowed",
            source="def validate_config() -> None:\n    return None\n",
            expected_codes=(),
            expected_lines=(),
        ),
        SfnRuleTestCase(
            description="validator bare return is allowed",
            source="def validate_config() -> None:\n    return\n",
            expected_codes=(),
            expected_lines=(),
        ),
        SfnRuleTestCase(
            description="enforcer returning value is flagged",
            source="async def enforce_policy() -> int:\n    return 1\n",
            expected_codes=("SFN001",),
            expected_lines=(2,),
        ),
        SfnRuleTestCase(
            description="check returning bool is not contracted",
            source="def check_value() -> bool:\n    return True\n",
            expected_codes=(),
            expected_lines=(),
        ),
        SfnRuleTestCase(
            description="nested helper return does not count for validator",
            source=(
                "def validate_config() -> None:\n"
                "    def build_value() -> int:\n"
                "        return 1\n"
                "    build_value()\n"
                "    return None\n"
            ),
            expected_codes=(),
            expected_lines=(),
        ),
        SfnRuleTestCase(
            description="custom no-return writer returning value is flagged",
            source="def write_record() -> int:\n    return 1\n",
            contracts={"write_*": "no-return"},
            expected_codes=("SFN001",),
            expected_lines=(2,),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_function_contracts_when_checking_returns_then_flags_meaningful_values(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: SfnRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_naming_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines
