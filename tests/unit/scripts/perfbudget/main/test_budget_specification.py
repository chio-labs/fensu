"""Behavior tests for backend-aware budget specification resolution."""

from __future__ import annotations

import pytest

from scripts.perfbudget._helpers.specification import resolved_budget_spec
from scripts.perfbudget.models import BudgetSpec
from tests.unit.scripts.perfbudget.main._test_types import SpecResolutionTestCase


@pytest.mark.parametrize(
    "test_case",
    [
        SpecResolutionTestCase(
            description="python backend receives the python default ceilings",
            backend="python",
            uncached_ceiling=None,
            cold_ceiling=None,
            warm_ceiling=None,
            edit_ceiling=None,
            expected_uncached=30.0,
            expected_cold=35.0,
            expected_warm=5.0,
            expected_edit=10.0,
        ),
        SpecResolutionTestCase(
            description="native backend receives the tightened native ceilings",
            backend="native",
            uncached_ceiling=None,
            cold_ceiling=None,
            warm_ceiling=None,
            edit_ceiling=None,
            expected_uncached=18.0,
            expected_cold=22.0,
            expected_warm=5.0,
            expected_edit=8.0,
        ),
        SpecResolutionTestCase(
            description="explicit ceilings override every backend default",
            backend="native",
            uncached_ceiling=1.0,
            cold_ceiling=2.0,
            warm_ceiling=3.0,
            edit_ceiling=4.0,
            expected_uncached=1.0,
            expected_cold=2.0,
            expected_warm=3.0,
            expected_edit=4.0,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_backend_and_overrides_when_resolving_spec_then_returns_expected_ceilings(
    test_case: SpecResolutionTestCase,
) -> None:
    spec: BudgetSpec = resolved_budget_spec(
        backend=test_case.backend,
        files=1,
        seed=0,
        uncached_ceiling=test_case.uncached_ceiling,
        cold_ceiling=test_case.cold_ceiling,
        warm_ceiling=test_case.warm_ceiling,
        edit_ceiling=test_case.edit_ceiling,
        executable=None,
    )

    assert spec.backend == test_case.backend
    assert spec.uncached_ceiling == test_case.expected_uncached
    assert spec.cold_ceiling == test_case.expected_cold
    assert spec.warm_ceiling == test_case.expected_warm
    assert spec.edit_ceiling == test_case.expected_edit
