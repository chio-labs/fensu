"""Import-time effect rule catalogue entries."""

from __future__ import annotations

from strata.rules.authoring.models import RuleSpec
from strata.rules.authoring.types import Family
from strata.rules.roles.helpers.checks import no_import_time_side_effects
from strata.rules.roles.types import RoleCode


def effect_rules() -> tuple[RuleSpec, ...]:
    """Build import-time effect rules."""

    return (
        RuleSpec(
            code=RoleCode.NO_IMPORT_TIME_SIDE_EFFECTS,
            family=Family.ROLES,
            slug="no-import-time-side-effects",
            message="runtime modules must not execute standalone calls during import",
            remediation=(
                "Move the operation into an explicit function or assign a pure constructor result."
            ),
            check=no_import_time_side_effects,
        ),
    )
