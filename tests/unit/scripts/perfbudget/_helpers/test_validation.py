"""Tests for repeated performance matrix validation."""

import pytest

from scripts.perfbudget._helpers.validation import repeated_run_failures
from scripts.perfbudget.models import ScenarioFailure, ScenarioResult
from tests.unit.scripts.perfbudget._helpers._test_types import RepeatedRunValidationTestCase


@pytest.mark.parametrize(
    "test_case",
    [
        RepeatedRunValidationTestCase(
            description="stable repeated output has no failure",
            first_hash="a" * 64,
            second_hash="a" * 64,
            expected_failure_count=0,
        ),
        RepeatedRunValidationTestCase(
            description="changed repeated output reports one failure",
            first_hash="a" * 64,
            second_hash="b" * 64,
            expected_failure_count=1,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_repeated_scenario_outputs_when_validating_then_reports_identity_changes(
    test_case: RepeatedRunValidationTestCase,
) -> None:
    first: ScenarioResult = ScenarioResult(
        name="warm",
        seconds=1.0,
        exit_code=1,
        output_sha256=test_case.first_hash,
        cache_stats="",
        fallback_warned=False,
        max_rss_kib=100,
    )
    second: ScenarioResult = ScenarioResult(
        name="warm",
        seconds=1.1,
        exit_code=1,
        output_sha256=test_case.second_hash,
        cache_stats="",
        fallback_warned=False,
        max_rss_kib=110,
    )

    failures: tuple[ScenarioFailure, ...] = repeated_run_failures(
        runs=({"warm": first}, {"warm": second})
    )

    assert len(failures) == test_case.expected_failure_count
