"""Tests enforcing hermetic rule execution outside the tracked project facade."""

from __future__ import annotations

import pytest

from tests.unit.src.strata.rules.authoring._test_types import HermeticityTestCase
from tests.unit.src.strata.rules.authoring.helpers import HermeticityScan, scan_rules_hermeticity


@pytest.mark.parametrize(
    "test_case",
    [
        HermeticityTestCase(
            description="rule execution modules perform no untracked side-effect operations",
            excluded_packages=("catalog", "testing"),
            expected_minimum_modules=50,
            expected_violations=(),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_rule_execution_modules_when_scanning_then_finds_no_untracked_operations(
    test_case: HermeticityTestCase,
) -> None:
    scan: HermeticityScan = scan_rules_hermeticity(
        excluded_packages=test_case.excluded_packages,
    )

    assert scan.module_count >= test_case.expected_minimum_modules
    assert scan.violations == test_case.expected_violations
