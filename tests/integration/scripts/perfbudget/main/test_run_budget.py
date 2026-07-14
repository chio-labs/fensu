"""Behavior tests for budget scenario enforcement."""

from __future__ import annotations

import pytest

from tests.integration.scripts.perfbudget.main._test_types import BudgetRunTestCase
from tests.integration.scripts.perfbudget.main.helpers import uniform_budget_run


@pytest.mark.parametrize(
    "test_case",
    [
        BudgetRunTestCase(
            description="scenarios within a generous ceiling pass",
            file_target=120,
            seed=0,
            ceiling_seconds=300.0,
            expected_exit_code=0,
        ),
        BudgetRunTestCase(
            description="scenarios beyond an impossible ceiling fail",
            file_target=120,
            seed=0,
            ceiling_seconds=0.000001,
            expected_exit_code=1,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_ceiling_when_running_budget_then_returns_expected_exit_code(
    test_case: BudgetRunTestCase,
) -> None:
    exit_code: int = uniform_budget_run(
        file_target=test_case.file_target,
        seed=test_case.seed,
        ceiling_seconds=test_case.ceiling_seconds,
    )

    assert exit_code == test_case.expected_exit_code
