"""Tests for the Fault vocabulary model."""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from fensu.rules.authoring.models import Fault
from tests.unit.src.fensu.rules.authoring._test_types import FaultFormatTestCase


@pytest.mark.parametrize(
    "test_case",
    [
        FaultFormatTestCase(
            description="renders code, relative path, line, column, and message",
            code="FFR001",
            path=Path("/repo/src/fensu/rules/authoring/models.py"),
            message="models.py must contain only models",
            line=12,
            column=4,
            root=Path("/repo"),
            expected_rendered=(
                "src/fensu/rules/authoring/models.py:12:4: FFR001 "
                "models.py must contain only models"
            ),
        ),
        FaultFormatTestCase(
            description="renders placeholder dashes when line and column are absent",
            code="FFL101",
            path=Path("/repo/src/fensu/cli/main/entry.py"),
            message="layer boundary crossed",
            line=None,
            column=None,
            root=Path("/repo"),
            expected_rendered="src/fensu/cli/main/entry.py:-:-: FFL101 layer boundary crossed",
        ),
        FaultFormatTestCase(
            description="keeps an absolute path when it is outside the root",
            code="FFH001",
            path=Path("/other/place/file.py"),
            message="outside repo",
            line=1,
            column=0,
            root=Path("/repo"),
            expected_rendered="/other/place/file.py:1:0: FFH001 outside repo",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_fault_when_formatting_then_renders_expected_line(
    test_case: FaultFormatTestCase,
) -> None:
    fault: Fault = Fault(
        code=test_case.code,
        path=test_case.path,
        message=test_case.message,
        line=test_case.line,
        column=test_case.column,
    )

    rendered: str = fault.format(test_case.root)

    assert rendered == test_case.expected_rendered


@pytest.mark.parametrize(
    "test_case",
    [
        FaultFormatTestCase(
            description="mutating a fault field raises FrozenInstanceError",
            code="FFR001",
            path=Path("/repo/a.py"),
            message="m",
            line=1,
            column=1,
            root=Path("/repo"),
            expected_rendered="FFR002",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_fault_when_assigning_field_then_raises_frozen_instance_error(
    test_case: FaultFormatTestCase,
) -> None:
    fault: Fault = Fault(code=test_case.code, path=test_case.path, message=test_case.message)

    with pytest.raises(dataclasses.FrozenInstanceError):
        fault.code = test_case.expected_rendered  # ty: ignore[invalid-assignment]
