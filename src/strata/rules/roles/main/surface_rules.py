"""Role surface rule catalogue entries."""

from __future__ import annotations

from strata.rules.authoring.models import RuleSpec
from strata.rules.authoring.types import Family, RuleCheck
from strata.rules.roles.helpers.checks import (
    entry_module_shape,
    init_module_empty,
    main_entry_name_collision,
    no_internal_helper_exports,
    no_reexport_shim,
    public_surface_shape,
)
from strata.rules.roles.types import RoleCode


def surface_rules() -> tuple[RuleSpec, ...]:
    """Build role surface rules."""

    return (
        _rule(
            code=RoleCode.ENTRY_MODULE_SHAPE, slug="entry-module-shape", check=entry_module_shape
        ),
        _rule(code=RoleCode.INIT_MODULE_EMPTY, slug="init-module-empty", check=init_module_empty),
        _rule(code=RoleCode.NO_REEXPORT_SHIM, slug="no-reexport-shim", check=no_reexport_shim),
        _rule(
            code=RoleCode.NO_INTERNAL_HELPER_EXPORTS,
            slug="no-internal-helper-exports",
            check=no_internal_helper_exports,
        ),
        _rule(
            code=RoleCode.MAIN_ENTRY_NAME_COLLISION,
            slug="main-entry-name-collision",
            check=main_entry_name_collision,
        ),
        _rule(
            code=RoleCode.PUBLIC_SURFACE_SHAPE,
            slug="public-surface-shape",
            check=public_surface_shape,
        ),
    )


def _rule(*, code: RoleCode, slug: str, check: RuleCheck) -> RuleSpec:
    return RuleSpec(
        code=code,
        family=Family.ROLES,
        slug=slug,
        message=f"role surface violation ({code.value})",
        check=check,
    )
