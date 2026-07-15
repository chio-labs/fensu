"""Behavior tests for native-backend budget scenario enforcement."""

from __future__ import annotations

from typing import Any

import pytest

from strata.analysis.constants import NATIVE_FACT_MODULE_NAME

strata_facts: Any = pytest.importorskip(NATIVE_FACT_MODULE_NAME)

from tests.integration.scripts.perfbudget.main._test_types import (  # noqa: E402
    BudgetRunTestCase,
)
from tests.integration.scripts.perfbudget.main.helpers import (  # noqa: E402
    uniform_budget_run,
)


@pytest.mark.parametrize(
    "test_case",
    [
        BudgetRunTestCase(
            description="native scenarios within a generous ceiling pass",
            backend="native",
            file_target=120,
            seed=0,
            runs=1,
            ceiling_seconds=300.0,
            expected_exit_code=0,
            expected_run_count=1,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_native_backend_when_running_budget_then_returns_expected_exit_code(
    test_case: BudgetRunTestCase,
) -> None:
    exit_code: int = uniform_budget_run(
        backend=test_case.backend,
        file_target=test_case.file_target,
        seed=test_case.seed,
        runs=test_case.runs,
        ceiling_seconds=test_case.ceiling_seconds,
    )

    assert exit_code == test_case.expected_exit_code
