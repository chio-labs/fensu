"""Python boundary tests for Rust-owned core-rule families."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.integration.src.fensu.rules.catalog._test_types import NativeCoreBoundaryTestCase
from tests.integration.src.fensu.rules.catalog.helpers import evaluate_native_boundary


@pytest.mark.parametrize(
    "test_case",
    [
        NativeCoreBoundaryTestCase(
            description="annotation diagnostic crosses the native boundary",
            rule_code="FFA001",
            files=(
                ("src/pkg/domain/core/models.py", "def run(value) -> None:\n    return None\n"),
            ),
            expected_path="src/pkg/domain/core/models.py",
            expected_line=1,
        ),
        NativeCoreBoundaryTestCase(
            description="hygiene diagnostic crosses the native boundary",
            rule_code="FFH001",
            files=(
                (
                    "src/pkg/domain/core/models.py",
                    '"""Summary.\n\nDetails.\n"""\nvalue: int = 1\n',
                ),
            ),
            expected_path="src/pkg/domain/core/models.py",
            expected_line=1,
        ),
        NativeCoreBoundaryTestCase(
            description="layer diagnostic crosses the native boundary",
            rule_code="FFL001",
            files=(("src/pkg/domain/core/main/run.py", "from . import local\n"),),
            expected_path="src/pkg/domain/core/main/run.py",
            expected_line=1,
        ),
        NativeCoreBoundaryTestCase(
            description="naming diagnostic crosses the native boundary",
            rule_code="FFN001",
            files=(
                (
                    "src/pkg/domain/core/_helpers/tools.py",
                    "def validate_config() -> bool:\n    return True\n",
                ),
            ),
            expected_path="src/pkg/domain/core/_helpers/tools.py",
            expected_line=2,
        ),
        NativeCoreBoundaryTestCase(
            description="role diagnostic crosses the native boundary",
            rule_code="FFR001",
            files=(("src/pkg/domain/core/models.py", "def build() -> None:\n    return None\n"),),
            expected_path="src/pkg/domain/core/models.py",
            expected_line=1,
        ),
        NativeCoreBoundaryTestCase(
            description="shape diagnostic crosses the native boundary",
            rule_code="FFS010",
            files=(
                (
                    "src/pkg/domain/core/_helpers/tools.py",
                    "def run(a: int, b: int, c: int, d: int, e: int, f: int, g: int, h: int, i: int, j: int, k: int) -> None:\n    return None\n",
                ),
            ),
            expected_path="src/pkg/domain/core/_helpers/tools.py",
            expected_line=1,
        ),
        NativeCoreBoundaryTestCase(
            description="test-policy diagnostic crosses the native boundary",
            rule_code="FFT106",
            files=(
                ("src/pkg/domain/__init__.py", ""),
                (
                    "tests/unit/src/pkg/domain/test_example.py",
                    "pairs = [(left, right) for left in (1, 2) for right in (3, 4)]\n",
                ),
            ),
            expected_path="tests/unit/src/pkg/domain/test_example.py",
            expected_line=1,
            tests=("tests",),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_native_core_family_when_evaluating_then_crosses_python_boundary(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: NativeCoreBoundaryTestCase,
) -> None:
    result, rule = evaluate_native_boundary(
        test_case=test_case,
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
    )

    assert rule.check is None
    assert tuple(fault.code for fault in result.faults) == (test_case.rule_code,)
    assert tuple(fault.path.relative_to(tmp_path).as_posix() for fault in result.faults) == (
        test_case.expected_path,
    )
    assert tuple(fault.line for fault in result.faults) == (test_case.expected_line,)
