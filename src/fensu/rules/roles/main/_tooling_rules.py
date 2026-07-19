"""Tooling entrypoint and package role catalogue entries."""

from __future__ import annotations

from fensu.rules.authoring.models import RuleSpec
from fensu.rules.authoring.types import Family
from fensu.rules.roles._helpers.checks import (
    custom_rule_test_coverage,
    descriptive_rule_module_names,
    rules_role_content,
    tooling_entrypoint_delegation,
    tooling_entrypoint_line_count,
    tooling_entrypoint_shape,
    tooling_package_layout,
)
from fensu.rules.roles.types import RoleCode


def tooling_rules() -> tuple[RuleSpec, ...]:
    """Build tooling-specific structure rules."""

    return (
        RuleSpec(
            code=RoleCode.TOOLING_ENTRYPOINT_SHAPE,
            family=Family.ROLES,
            slug="tooling-entrypoint-shape",
            message="direct scripts must remain focused command adapters",
            remediation=(
                "Keep one public main(), optional private _parse_args() and _build_parser(), and "
                "move implementation into a scripts/<tool>/main/ entry."
            ),
            check=tooling_entrypoint_shape,
        ),
        RuleSpec(
            code=RoleCode.TOOLING_ENTRYPOINT_DELEGATION,
            family=Family.ROLES,
            slug="tooling-entrypoint-delegation",
            message="direct scripts must delegate to an imported main/ entrypoint",
            remediation=(
                "Import a typed entry function from a runtime or scripts/<tool>/main/ module and "
                "return its result from main()."
            ),
            check=tooling_entrypoint_delegation,
        ),
        RuleSpec(
            code=RoleCode.TOOLING_ENTRYPOINT_LINE_COUNT,
            family=Family.ROLES,
            slug="tooling-entrypoint-line-count",
            message="direct scripts must stay below the configured line limit",
            remediation="Move command implementation into a named tooling or runtime package.",
            check=tooling_entrypoint_line_count,
        ),
        RuleSpec(
            code=RoleCode.RULES_ROLE_CONTENT,
            family=Family.ROLES,
            slug="rules-role-content",
            message="tooling rules/ modules may contain only decorated rule declarations",
            remediation=(
                "Keep imports and @rule functions here; move supporting implementation into "
                "_helpers/, classes/, models.py, types.py, constants.py, or exceptions.py."
            ),
            check=rules_role_content,
        ),
        RuleSpec(
            code=RoleCode.TOOLING_PACKAGE_LAYOUT,
            family=Family.ROLES,
            slug="tooling-package-layout",
            message="tool packages must organize implementation through explicit roles",
            remediation=(
                "Use main/, _helpers/, classes/, rules/, models.py, types.py, constants.py, or "
                "exceptions.py directly beneath scripts/<tool>/."
            ),
            check=tooling_package_layout,
        ),
        RuleSpec(
            code=RoleCode.DESCRIPTIVE_RULE_MODULE_NAMES,
            family=Family.ROLES,
            slug="descriptive-rule-module-names",
            message=(
                "rule module filenames must describe their policy rather than repeat one rule code"
            ),
            remediation=(
                "Rename the module after the policy or rule family it implements, using a name "
                "such as conditional_test_flow.py instead of fft104.py."
            ),
            check=descriptive_rule_module_names,
        ),
        RuleSpec(
            code=RoleCode.CUSTOM_RULE_TEST_COVERAGE,
            family=Family.ROLES,
            slug="custom-rule-test-coverage",
            message="configured custom rules must have statically declared public-harness cases",
            remediation=(
                "Add parametrized RuleCase coverage for the rule's passing and failing boundaries "
                "using evaluate_rule."
            ),
            check=custom_rule_test_coverage,
        ),
    )
