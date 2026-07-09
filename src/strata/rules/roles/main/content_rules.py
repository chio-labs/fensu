"""Role-content rule catalogue entries."""

from __future__ import annotations

from strata.rules.authoring.models import RuleSpec
from strata.rules.authoring.types import Family
from strata.rules.roles.helpers.checks import (
    constants_only_constants,
    exceptions_only_exceptions,
    models_only_models,
    types_only_types,
)
from strata.rules.roles.types import RoleCode


def content_rules() -> tuple[RuleSpec, ...]:
    """Build role-content rules."""

    return (
        RuleSpec(
            code=RoleCode.MODELS_ONLY_MODELS,
            family=Family.ROLES,
            slug="models-only-models",
            message="models role files may contain only structured runtime models",
            check=models_only_models,
        ),
        RuleSpec(
            code=RoleCode.TYPES_ONLY_TYPES,
            family=Family.ROLES,
            slug="types-only-types",
            message="types role files may contain only type-layer declarations",
            check=types_only_types,
        ),
        RuleSpec(
            code=RoleCode.CONSTANTS_ONLY_CONSTANTS,
            family=Family.ROLES,
            slug="constants-only-constants",
            message="constants role files may contain only assignments and imports",
            check=constants_only_constants,
        ),
        RuleSpec(
            code=RoleCode.EXCEPTIONS_ONLY_EXCEPTIONS,
            family=Family.ROLES,
            slug="exceptions-only-exceptions",
            message="exceptions role files may contain only custom exceptions",
            check=exceptions_only_exceptions,
        ),
    )
