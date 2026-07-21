"""Misplaced role-declaration rule catalogue entries."""

from __future__ import annotations

from fensu.rules.authoring.models import RuleSpec
from fensu.rules.authoring.types import Family
from fensu.rules.roles.types import RoleCode


def misplaced_rules() -> tuple[RuleSpec, ...]:
    """Build misplaced role-declaration rules."""

    return (
        RuleSpec(
            code=RoleCode.MODEL_DECLARATION_OUTSIDE_MODELS,
            family=Family.ROLES,
            slug="model-declaration-outside-models",
            message="structured runtime models must be defined in the models role",
            remediation=(
                "Move the dataclass or structured model into models.py or a models/ package."
            ),
        ),
        RuleSpec(
            code=RoleCode.TYPE_DECLARATION_OUTSIDE_TYPES,
            family=Family.ROLES,
            slug="type-declaration-outside-types",
            message="type-layer declarations must be defined in the types role",
            remediation="Move the protocol, enum, TypedDict, or public type alias into types.py.",
        ),
        RuleSpec(
            code=RoleCode.CONSTANT_OUTSIDE_CONSTANTS,
            family=Family.ROLES,
            slug="constant-outside-constants",
            message="public uppercase constants must be defined in the constants role",
            remediation="Move the public constant into constants.py and import it from there.",
        ),
        RuleSpec(
            code=RoleCode.EXCEPTION_DECLARATION_OUTSIDE_EXCEPTIONS,
            family=Family.ROLES,
            slug="exception-declaration-outside-exceptions",
            message="custom exceptions must be defined in the exceptions role",
            remediation="Move the exception class into exceptions.py or an exceptions/ package.",
        ),
    )
