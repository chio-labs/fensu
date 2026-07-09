"""Tests for roles rules."""

from __future__ import annotations

from pathlib import Path

import pytest

from strata.evaluation.core.models import EvaluationResult
from tests.unit.src.strata.rules.roles.main._test_types import SfrRuleTestCase
from tests.unit.src.strata.rules.roles.main.helpers import evaluate_role_test_case


@pytest.mark.parametrize(
    "test_case",
    [
        SfrRuleTestCase(
            description="runtime function in models role is flagged",
            rule_code="SFR001",
            relative_path="domain/core/models.py",
            source="def build() -> None:\n    return None\n",
            expected_codes=("SFR001",),
            expected_lines=(1,),
        ),
        SfrRuleTestCase(
            description="dataclass in models role is allowed",
            rule_code="SFR001",
            relative_path="domain/core/models.py",
            source=(
                "from dataclasses import dataclass\n\n"
                "@dataclass(frozen=True)\n"
                "class Result:\n"
                "    value: int\n"
            ),
            expected_codes=(),
            expected_lines=(),
        ),
        SfrRuleTestCase(
            description="runtime function in types role is flagged",
            rule_code="SFR002",
            relative_path="domain/core/types.py",
            source="def build() -> None:\n    return None\n",
            expected_codes=("SFR002",),
            expected_lines=(1,),
        ),
        SfrRuleTestCase(
            description="protocol in types role is allowed",
            rule_code="SFR002",
            relative_path="domain/core/types.py",
            source="from typing import Protocol\n\nclass Service(Protocol):\n    value: int\n",
            expected_codes=(),
            expected_lines=(),
        ),
        SfrRuleTestCase(
            description="class in constants role is flagged",
            rule_code="SFR003",
            relative_path="domain/core/constants.py",
            source="class Config:\n    value: int\n",
            expected_codes=("SFR003",),
            expected_lines=(1,),
        ),
        SfrRuleTestCase(
            description="assignment in constants role is allowed",
            rule_code="SFR003",
            relative_path="domain/core/constants.py",
            source="DEFAULT_VALUE: int = 1\n",
            expected_codes=(),
            expected_lines=(),
        ),
        SfrRuleTestCase(
            description="plain class in exceptions role is flagged",
            rule_code="SFR004",
            relative_path="domain/core/exceptions.py",
            source="class Result:\n    value: int\n",
            expected_codes=("SFR004",),
            expected_lines=(1,),
        ),
        SfrRuleTestCase(
            description="custom error in exceptions role is allowed",
            rule_code="SFR004",
            relative_path="domain/core/exceptions.py",
            source="class ConfigError(Exception):\n    pass\n",
            expected_codes=(),
            expected_lines=(),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_role_files_when_checking_content_then_flags_only_foreign_declarations(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: SfrRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_role_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        SfrRuleTestCase(
            description="dataclass outside models role is flagged",
            rule_code="SFR101",
            relative_path="domain/core/helpers/results.py",
            source=(
                "from dataclasses import dataclass\n\n"
                "@dataclass(frozen=True)\n"
                "class Result:\n"
                "    value: int\n"
            ),
            expected_codes=("SFR101",),
            expected_lines=(4,),
        ),
        SfrRuleTestCase(
            description="private dataclass outside models role is allowed",
            rule_code="SFR101",
            relative_path="domain/core/helpers/results.py",
            source=(
                "from dataclasses import dataclass\n\n"
                "@dataclass(frozen=True)\n"
                "class _Result:\n"
                "    value: int\n"
            ),
            expected_codes=(),
            expected_lines=(),
        ),
        SfrRuleTestCase(
            description="protocol outside types role is flagged",
            rule_code="SFR102",
            relative_path="domain/core/classes/service.py",
            source="from typing import Protocol\n\nclass Service(Protocol):\n    value: int\n",
            expected_codes=("SFR102",),
            expected_lines=(3,),
        ),
        SfrRuleTestCase(
            description="private protocol in helpers role is allowed",
            rule_code="SFR102",
            relative_path="domain/core/helpers/service.py",
            source="from typing import Protocol\n\nclass _Service(Protocol):\n    value: int\n",
            expected_codes=(),
            expected_lines=(),
        ),
        SfrRuleTestCase(
            description="public uppercase constant outside constants role is flagged",
            rule_code="SFR103",
            relative_path="domain/core/helpers/values.py",
            source="DEFAULT_VALUE: int = 1\n",
            expected_codes=("SFR103",),
            expected_lines=(1,),
        ),
        SfrRuleTestCase(
            description="private uppercase constant outside constants role is allowed",
            rule_code="SFR103",
            relative_path="domain/core/helpers/values.py",
            source="_DEFAULT_VALUE: int = 1\n",
            expected_codes=(),
            expected_lines=(),
        ),
        SfrRuleTestCase(
            description="custom error outside exceptions role is flagged",
            rule_code="SFR104",
            relative_path="domain/core/helpers/errors.py",
            source="class ConfigError(Exception):\n    pass\n",
            expected_codes=("SFR104",),
            expected_lines=(1,),
        ),
        SfrRuleTestCase(
            description="plain class outside exceptions role is allowed",
            rule_code="SFR104",
            relative_path="domain/core/classes/result.py",
            source="class Result:\n    value: int\n",
            expected_codes=(),
            expected_lines=(),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_declarations_when_checking_ownership_then_flags_only_misplaced_roles(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: SfrRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_role_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        SfrRuleTestCase(
            description="generic common filename is flagged",
            rule_code="SFR201",
            relative_path="domain/core/common.py",
            source="value: int = 1\n",
            expected_codes=("SFR201",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="domain-specific filename is allowed",
            rule_code="SFR201",
            relative_path="domain/core/settings.py",
            source="value: int = 1\n",
            expected_codes=(),
            expected_lines=(),
        ),
        SfrRuleTestCase(
            description="helpers module filename is flagged",
            rule_code="SFR202",
            relative_path="domain/core/helpers.py",
            source="value: int = 1\n",
            expected_codes=("SFR202",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="classes module filename is flagged",
            rule_code="SFR203",
            relative_path="domain/core/classes.py",
            source="class Service:\n    value: int\n",
            expected_codes=("SFR203",),
            expected_lines=(None,),
        ),
        SfrRuleTestCase(
            description="public plain class in helpers is flagged",
            rule_code="SFR205",
            relative_path="domain/core/helpers/service.py",
            source="class Service:\n    value: int\n",
            expected_codes=("SFR205",),
            expected_lines=(1,),
        ),
        SfrRuleTestCase(
            description="private plain class in helpers is allowed",
            rule_code="SFR205",
            relative_path="domain/core/helpers/service.py",
            source="class _Service:\n    value: int\n",
            expected_codes=(),
            expected_lines=(),
        ),
        SfrRuleTestCase(
            description="plain class in classes role is unaffected",
            rule_code="SFR205",
            relative_path="domain/core/classes/service.py",
            source="class Service:\n    value: int\n",
            expected_codes=(),
            expected_lines=(),
        ),
        SfrRuleTestCase(
            description="public dataclass in helpers is left to model ownership rule",
            rule_code="SFR205",
            relative_path="domain/core/helpers/results.py",
            source=(
                "from dataclasses import dataclass\n\n"
                "@dataclass(frozen=True)\n"
                "class Result:\n"
                "    value: int\n"
            ),
            expected_codes=(),
            expected_lines=(),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_role_names_and_helper_classes_when_checking_then_flags_only_violations(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: SfrRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_role_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines
