"""Role layout rule catalogue entries."""

from __future__ import annotations

from strata.rules.authoring.models import RuleSpec
from strata.rules.authoring.types import Family, RuleCheck
from strata.rules.roles.helpers.checks import (
    helpers_package_layout,
    main_package_layout,
    nested_direct_modules,
    nested_direct_subpackages,
    top_level_direct_modules,
    top_level_role_placement,
)
from strata.rules.roles.types import RoleCode


def layout_rules() -> tuple[RuleSpec, ...]:
    """Build role layout rules."""

    return (
        _rule(
            code=RoleCode.HELPERS_PACKAGE_LAYOUT,
            slug="helpers-package-layout",
            check=helpers_package_layout,
        ),
        _rule(
            code=RoleCode.MAIN_PACKAGE_LAYOUT,
            slug="main-package-layout",
            check=main_package_layout,
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
            code=RoleCode.TOP_LEVEL_ROLE_PLACEMENT,
            slug="top-level-role-placement",
            check=top_level_role_placement,
        ),
        _rule(
            code=RoleCode.TOP_LEVEL_DIRECT_MODULES,
            slug="top-level-direct-modules",
            check=top_level_direct_modules,
        ),
    )


def _rule(*, code: RoleCode, slug: str, check: RuleCheck) -> RuleSpec:
    return RuleSpec(
        code=code,
        family=Family.ROLES,
        slug=slug,
        message=f"role layout violation ({code.value})",
        check=check,
    )
