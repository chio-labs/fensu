"""Behavior tests for budget scenario enforcement."""

from __future__ import annotations

import pytest

from scripts.perfbudget.main.run_budget import run_budget
from tests.integration.scripts.perfbudget.main._test_types import (
    BudgetRunTestCase,
    NativeUnavailableTestCase,
)
from tests.integration.scripts.perfbudget.main.helpers import uniform_budget_run


@pytest.mark.parametrize(
    "test_case",
    [
        BudgetRunTestCase(
            description="scenarios within a generous ceiling pass",
            backend="python",
            file_target=120,
            seed=0,
            ceiling_seconds=300.0,
            expected_exit_code=0,
        ),
        BudgetRunTestCase(
            description="scenarios beyond an impossible ceiling fail",
            backend="python",
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
        backend=test_case.backend,
        file_target=test_case.file_target,
        seed=test_case.seed,
        ceiling_seconds=test_case.ceiling_seconds,
    )

    assert exit_code == test_case.expected_exit_code


@pytest.mark.parametrize(
    "test_case",
    [
        NativeUnavailableTestCase(
            description="a native budget without the extension fails fast",
            expected_exit_code=1,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_missing_native_extension_when_running_native_budget_then_fails_fast(
    test_case: NativeUnavailableTestCase,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "scripts.perfbudget.main.run_budget.is_native_backend_available",
        lambda: False,
    )

    exit_code: int = run_budget(
        backend="native",
        files=1,
        seed=0,
        uncached_ceiling=None,
        cold_ceiling=None,
        warm_ceiling=None,
        edit_ceiling=None,
    )

    assert exit_code == test_case.expected_exit_code
