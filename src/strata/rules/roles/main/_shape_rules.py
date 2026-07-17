"""Role module-shape rule catalogue entries."""

from __future__ import annotations

from strata.rules.authoring.models import RuleSpec
from strata.rules.authoring.types import Family, RuleCheck
from strata.rules.roles._helpers.checks import (
    classes_one_class_per_module,
    helpers_package_shape,
    private_definition_ordering,
    source_file_line_count,
)
from strata.rules.roles._helpers.metadata import role_rule_details
from strata.rules.roles.types import RoleCode


def shape_rules() -> tuple[RuleSpec, ...]:
    """Build role module-shape rules."""

    return (
        _rule(
            code=RoleCode.CLASSES_ONE_CLASS_PER_MODULE,
            slug="classes-one-class-per-module",
            check=classes_one_class_per_module,
        ),
        _rule(
            code=RoleCode.HELPERS_PACKAGE_SHAPE,
            slug="helpers-package-shape",
            check=helpers_package_shape,
        ),
        _rule(
            code=RoleCode.PRIVATE_DEFINITION_ORDERING,
            slug="private-definition-ordering",
            check=private_definition_ordering,
        ),
        _rule(
            code=RoleCode.SOURCE_FILE_LINE_COUNT,
            slug="source-file-line-count",
            check=source_file_line_count,
        ),
    )


def _rule(*, code: RoleCode, slug: str, check: RuleCheck) -> RuleSpec:
    message, remediation = role_rule_details(code)
    return RuleSpec(
        code=code,
        family=Family.ROLES,
        slug=slug,
        message=message,
        remediation=remediation,
        check=check,
    )
