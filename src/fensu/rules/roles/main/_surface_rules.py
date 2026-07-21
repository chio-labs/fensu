"""Role surface rule catalogue entries."""

from __future__ import annotations

from fensu.rules.authoring.models import RuleSpec
from fensu.rules.authoring.types import Family
from fensu.rules.roles._helpers.metadata import role_rule_details
from fensu.rules.roles.types import RoleCode


def surface_rules() -> tuple[RuleSpec, ...]:
    """Build role surface rules."""

    return (
        _rule(code=RoleCode.ENTRY_MODULE_SHAPE, slug="entry-module-shape"),
        _rule(code=RoleCode.INIT_MODULE_EMPTY, slug="init-module-empty"),
        _rule(code=RoleCode.NO_REEXPORT_SHIM, slug="no-reexport-shim"),
        _rule(
            code=RoleCode.NO_INTERNAL_HELPER_EXPORTS,
            slug="no-internal-helper-exports",
        ),
        _rule(
            code=RoleCode.MAIN_ENTRY_NAME_COLLISION,
            slug="main-entry-name-collision",
        ),
        _rule(
            code=RoleCode.PUBLIC_SURFACE_SHAPE,
            slug="public-surface-shape",
        ),
    )


def _rule(*, code: RoleCode, slug: str) -> RuleSpec:
    message, remediation = role_rule_details(code)
    return RuleSpec(
        code=code,
        family=Family.ROLES,
        slug=slug,
        message=message,
        remediation=remediation,
    )
