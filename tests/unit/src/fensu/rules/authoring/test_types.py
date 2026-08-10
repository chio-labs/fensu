"""Tests for the rule-definition enums."""

from __future__ import annotations

import pytest

from fensu.rules.authoring.types import Family, RuleKind, Severity, Threshold
from tests.unit.src.fensu.rules.authoring._test_types import EnumMembersTestCase


@pytest.mark.parametrize(
    "test_case",
    [
        EnumMembersTestCase(
            description="Family has all ten taxonomy members",
            actual_members={member.name: member.value for member in Family},
            expected_members={
                "LAYERS": "layers",
                "ROLES": "roles",
                "SHAPE": "shape",
                "NAMING": "naming",
                "HYGIENE": "hygiene",
                "TESTS": "tests",
                "ANNOTATIONS": "annotations",
                "CONTRACTS": "contracts",
                "PARSING": "parsing",
                "CUSTOM": "custom",
            },
        ),
        EnumMembersTestCase(
            description="Severity has error and warning",
            actual_members={member.name: member.value for member in Severity},
            expected_members={"ERROR": "error", "WARNING": "warning"},
        ),
        EnumMembersTestCase(
            description="RuleKind has core, native pack, and custom",
            actual_members={member.name: member.value for member in RuleKind},
            expected_members={"CORE": "core", "PACK": "pack", "CUSTOM": "custom"},
        ),
        EnumMembersTestCase(
            description="Threshold has all twenty-five named limits",
            actual_members={member.name: member.value for member in Threshold},
            expected_members={
                "MAX_STATEMENTS": "max_statements",
                "MAX_DISTINCT_CALLS": "max_distinct_calls",
                "MAX_LOCALS": "max_locals",
                "MAX_FILE_LINES": "max_file_lines",
                "MAX_HELPERS_CONTAINER_MODULES": "max_helpers_container_modules",
                "MAX_MAIN_CONTAINER_MODULES": "max_main_container_modules",
                "MAX_ROLE_DEPTH": "max_role_depth",
                "MAX_POSITIONAL_ARGS": "max_positional_args",
                "MAX_ARGUMENTS": "max_arguments",
                "MAX_STATEMENTS_GLOBAL": "max_statements_global",
                "MAX_SCRIPT_ENTRYPOINT_LINES": "max_script_entrypoint_lines",
                "MIN_SHARED_DOMAIN_PREFIX_PACKAGES": "min_shared_domain_prefix_packages",
                "MIN_CUSTOM_RULE_TEST_CASES": "min_custom_rule_test_cases",
                "MAX_IMPORTED_BINDINGS": "max_imported_bindings",
                "MAX_PUBLIC_EXPORTS": "max_public_exports",
                "MAX_ROUTE_SCRIPT_LINES": "max_route_script_lines",
                "MAX_COMPONENT_SCRIPT_LINES": "max_component_script_lines",
                "MAX_STATE_LINES": "max_state_lines",
                "MAX_STATE_PUBLIC_MEMBERS": "max_state_public_members",
                "MAX_STATE_CELLS": "max_state_cells",
                "MAX_TOTAL_RUNES": "max_total_runes",
                "MAX_STATE_FUNCTIONS": "max_state_functions",
                "MAX_RESOURCE_FAMILIES": "max_resource_families",
                "MAX_API_LINES": "max_api_lines",
                "MAX_API_EXPORTS": "max_api_exports",
            },
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_enum_when_reading_members_then_matches_expected(
    test_case: EnumMembersTestCase,
) -> None:
    assert test_case.actual_members == test_case.expected_members
