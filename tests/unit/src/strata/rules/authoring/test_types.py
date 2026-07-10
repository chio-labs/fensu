"""Tests for the rule-definition enums."""

from __future__ import annotations

import pytest

from strata.rules.authoring.types import Family, RuleKind, Severity, Threshold
from tests.unit.src.strata.rules.authoring._test_types import EnumMembersTestCase


@pytest.mark.parametrize(
    "test_case",
    [
        EnumMembersTestCase(
            description="Family has all eight taxonomy members",
            actual_members={member.name: member.value for member in Family},
            expected_members={
                "LAYERS": "layers",
                "ROLES": "roles",
                "SHAPE": "shape",
                "NAMING": "naming",
                "HYGIENE": "hygiene",
                "TESTS": "tests",
                "ANNOTATIONS": "annotations",
                "CUSTOM": "custom",
            },
        ),
        EnumMembersTestCase(
            description="Severity has error and warning",
            actual_members={member.name: member.value for member in Severity},
            expected_members={"ERROR": "error", "WARNING": "warning"},
        ),
        EnumMembersTestCase(
            description="RuleKind has core and custom",
            actual_members={member.name: member.value for member in RuleKind},
            expected_members={"CORE": "core", "CUSTOM": "custom"},
        ),
        EnumMembersTestCase(
            description="Threshold has all ten named limits",
            actual_members={member.name: member.value for member in Threshold},
            expected_members={
                "MAX_STATEMENTS": "max_statements",
                "MAX_DISTINCT_CALLS": "max_distinct_calls",
                "MAX_LOCALS": "max_locals",
                "MAX_FILE_LINES": "max_file_lines",
                "MAX_FLAT_HELPER_MODULES": "max_flat_helper_modules",
                "MAX_FLAT_MAIN_MODULES": "max_flat_main_modules",
                "MAX_POSITIONAL_ARGS": "max_positional_args",
                "MAX_ARGUMENTS": "max_arguments",
                "MAX_STATEMENTS_GLOBAL": "max_statements_global",
                "MAX_SCRIPT_ENTRYPOINT_LINES": "max_script_entrypoint_lines",
            },
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_enum_when_reading_members_then_matches_expected(
    test_case: EnumMembersTestCase,
) -> None:
    assert test_case.actual_members == test_case.expected_members
