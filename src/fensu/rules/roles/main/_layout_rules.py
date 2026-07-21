"""Role layout rule catalogue entries."""

from __future__ import annotations

from fensu.rules.authoring.models import RuleSpec
from fensu.rules.authoring.types import ExecutionOwner, Family
from fensu.rules.roles._helpers.metadata import role_rule_details
from fensu.rules.roles.types import RoleCode


def layout_rules() -> tuple[RuleSpec, ...]:
    """Build role layout rules."""

    return (
        _rule(
            code=RoleCode.HELPERS_PACKAGE_LAYOUT,
            slug="helpers-package-layout",
            execution_owner=ExecutionOwner.PACKAGE,
        ),
        _rule(
            code=RoleCode.MAIN_PACKAGE_LAYOUT,
            slug="main-package-layout",
            execution_owner=ExecutionOwner.PACKAGE,
        ),
        _rule(
            code=RoleCode.HELPERS_RESERVED_ROLE_FILENAMES,
            slug="helpers-reserved-role-filenames",
        ),
        _rule(
            code=RoleCode.NESTED_DIRECT_MODULES,
            slug="nested-direct-modules",
        ),
        _rule(
            code=RoleCode.NESTED_DIRECT_SUBPACKAGES,
            slug="nested-direct-subpackages",
        ),
        _rule(
            code=RoleCode.TOP_LEVEL_DOMAIN_SHAPE,
            slug="top-level-domain-shape",
            execution_owner=ExecutionOwner.DOMAIN,
        ),
        _rule(
            code=RoleCode.TOP_LEVEL_DIRECT_MODULES,
            slug="top-level-direct-modules",
        ),
        _rule(
            code=RoleCode.SHARED_DOMAIN_PREFIX,
            slug="shared-domain-prefix",
            execution_owner=ExecutionOwner.SCOPE,
        ),
        _rule(
            code=RoleCode.LEAF_MAIN_BOUNDARY,
            slug="leaf-main-boundary",
            execution_owner=ExecutionOwner.LEAF,
        ),
    )


def _rule(
    *,
    code: RoleCode,
    slug: str,
    execution_owner: ExecutionOwner = ExecutionOwner.FILE,
) -> RuleSpec:
    message, remediation = role_rule_details(code)
    return RuleSpec(
        code=code,
        family=Family.ROLES,
        slug=slug,
        message=message,
        remediation=remediation,
        execution_owner=execution_owner,
    )
