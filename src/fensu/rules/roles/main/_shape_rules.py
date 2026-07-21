"""Role module-shape rule catalogue entries."""

from __future__ import annotations

from fensu.rules.authoring.models import RuleSpec
from fensu.rules.authoring.types import Family
from fensu.rules.roles._helpers.metadata import role_rule_details
from fensu.rules.roles.types import RoleCode


def shape_rules() -> tuple[RuleSpec, ...]:
    """Build role module-shape rules."""

    return (
        _rule(
            code=RoleCode.CLASSES_ONE_CLASS_PER_MODULE,
            slug="classes-one-class-per-module",
        ),
        _rule(
            code=RoleCode.HELPERS_PACKAGE_SHAPE,
            slug="helpers-package-shape",
        ),
        _rule(
            code=RoleCode.PRIVATE_DEFINITION_ORDERING,
            slug="private-definition-ordering",
        ),
        _rule(
            code=RoleCode.SOURCE_FILE_LINE_COUNT,
            slug="source-file-line-count",
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
