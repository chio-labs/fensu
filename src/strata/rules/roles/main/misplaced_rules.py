"""Misplaced role-declaration rule catalogue entries."""

from __future__ import annotations

from strata.rules.authoring.models import RuleSpec
from strata.rules.authoring.types import Family
from strata.rules.roles.helpers.checks import (
    constant_outside_constants,
    exception_declaration_outside_exceptions,
    model_declaration_outside_models,
    type_declaration_outside_types,
)
from strata.rules.roles.types import RoleCode


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
            check=model_declaration_outside_models,
        ),
        RuleSpec(
            code=RoleCode.TYPE_DECLARATION_OUTSIDE_TYPES,
            family=Family.ROLES,
            slug="type-declaration-outside-types",
            message="type-layer declarations must be defined in the types role",
            remediation="Move the protocol, enum, TypedDict, or public type alias into types.py.",
            check=type_declaration_outside_types,
        ),
        RuleSpec(
            code=RoleCode.CONSTANT_OUTSIDE_CONSTANTS,
            family=Family.ROLES,
            slug="constant-outside-constants",
            message="public uppercase constants must be defined in the constants role",
            remediation="Move the public constant into constants.py and import it from there.",
            check=constant_outside_constants,
        ),
        RuleSpec(
            code=RoleCode.EXCEPTION_DECLARATION_OUTSIDE_EXCEPTIONS,
            family=Family.ROLES,
            slug="exception-declaration-outside-exceptions",
            message="custom exceptions must be defined in the exceptions role",
            remediation="Move the exception class into exceptions.py or an exceptions/ package.",
            check=exception_declaration_outside_exceptions,
        ),
    )
