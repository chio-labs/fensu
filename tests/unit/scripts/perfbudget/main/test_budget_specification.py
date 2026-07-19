"""Behavior tests for native budget specification resolution."""

from __future__ import annotations

import pytest

from scripts.perfbudget._helpers.specification import resolved_budget_spec
from scripts.perfbudget.models import BudgetSpec
from tests.unit.scripts.perfbudget.main._test_types import SpecResolutionTestCase


@pytest.mark.parametrize(
    "test_case",
    [
        SpecResolutionTestCase(
            description="native checks receive the established performance ceilings",
            uncached_ceiling=None,
            cold_ceiling=None,
            warm_ceiling=None,
            edit_ceiling=None,
            version_ceiling=None,
            init_ceiling=None,
            expected_uncached=0.95,
            expected_cold=1.1,
            expected_warm=0.16,
            expected_edit=1.1,
            expected_version=0.03,
            expected_init=1.2,
        ),
        SpecResolutionTestCase(
            description="explicit ceilings override every native default",
            uncached_ceiling=1.0,
            cold_ceiling=2.0,
            warm_ceiling=3.0,
            edit_ceiling=4.0,
            version_ceiling=5.0,
            init_ceiling=6.0,
            expected_uncached=1.0,
            expected_cold=2.0,
            expected_warm=3.0,
            expected_edit=4.0,
            expected_version=5.0,
            expected_init=6.0,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_overrides_when_resolving_spec_then_returns_expected_ceilings(
    test_case: SpecResolutionTestCase,
) -> None:
    spec: BudgetSpec = resolved_budget_spec(
        files=1,
        seed=0,
        uncached_ceiling=test_case.uncached_ceiling,
        cold_ceiling=test_case.cold_ceiling,
        warm_ceiling=test_case.warm_ceiling,
        edit_ceiling=test_case.edit_ceiling,
        version_ceiling=test_case.version_ceiling,
        init_ceiling=test_case.init_ceiling,
        executable=None,
    )

    assert spec.uncached_ceiling == test_case.expected_uncached
    assert spec.cold_ceiling == test_case.expected_cold
    assert spec.warm_ceiling == test_case.expected_warm
    assert spec.edit_ceiling == test_case.expected_edit
    assert spec.version_ceiling == test_case.expected_version
    assert spec.init_ceiling == test_case.expected_init
