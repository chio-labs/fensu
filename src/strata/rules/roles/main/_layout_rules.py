"""Role layout rule catalogue entries."""

from __future__ import annotations

from strata.rules.authoring.models import RuleSpec
from strata.rules.authoring.types import ExecutionOwner, Family, RuleCheck
from strata.rules.roles._helpers.checks import (
    helpers_package_layout,
    helpers_reserved_role_filenames,
    leaf_main_boundary,
    main_package_layout,
    nested_direct_modules,
    nested_direct_subpackages,
    shared_domain_prefix,
    top_level_direct_modules,
    top_level_domain_shape,
)
from strata.rules.roles._helpers.metadata import role_rule_details
from strata.rules.roles.types import RoleCode


def layout_rules() -> tuple[RuleSpec, ...]:
    """Build role layout rules."""

    return (
        _rule(
            code=RoleCode.HELPERS_PACKAGE_LAYOUT,
            slug="helpers-package-layout",
            check=helpers_package_layout,
            execution_owner=ExecutionOwner.PACKAGE,
        ),
        _rule(
            code=RoleCode.MAIN_PACKAGE_LAYOUT,
            slug="main-package-layout",
            check=main_package_layout,
            execution_owner=ExecutionOwner.PACKAGE,
        ),
        _rule(
            code=RoleCode.HELPERS_RESERVED_ROLE_FILENAMES,
            slug="helpers-reserved-role-filenames",
            check=helpers_reserved_role_filenames,
        ),
        _rule(
            code=RoleCode.NESTED_DIRECT_MODULES,
            slug="nested-direct-modules",
            check=nested_direct_modules,
        ),
        _rule(
            code=RoleCode.NESTED_DIRECT_SUBPACKAGES,
            slug="nested-direct-subpackages",
            check=nested_direct_subpackages,
        ),
        _rule(
            code=RoleCode.TOP_LEVEL_DOMAIN_SHAPE,
            slug="top-level-domain-shape",
            check=top_level_domain_shape,
            execution_owner=ExecutionOwner.DOMAIN,
        ),
        _rule(
            code=RoleCode.TOP_LEVEL_DIRECT_MODULES,
            slug="top-level-direct-modules",
            check=top_level_direct_modules,
        ),
        _rule(
            code=RoleCode.SHARED_DOMAIN_PREFIX,
            slug="shared-domain-prefix",
            check=shared_domain_prefix,
            execution_owner=ExecutionOwner.SCOPE,
        ),
        _rule(
            code=RoleCode.LEAF_MAIN_BOUNDARY,
            slug="leaf-main-boundary",
            check=leaf_main_boundary,
            execution_owner=ExecutionOwner.LEAF,
        ),
    )


def _rule(
    *,
    code: RoleCode,
    slug: str,
    check: RuleCheck,
    execution_owner: ExecutionOwner = ExecutionOwner.FILE,
) -> RuleSpec:
    message, remediation = role_rule_details(code)
    return RuleSpec(
        code=code,
        family=Family.ROLES,
        slug=slug,
        message=message,
        remediation=remediation,
        check=check,
        execution_owner=execution_owner,
    )
