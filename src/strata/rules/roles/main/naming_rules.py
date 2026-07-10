"""Role naming and helper-content rule catalogue entries."""

from __future__ import annotations

from strata.rules.authoring.models import RuleSpec
from strata.rules.authoring.types import Family
from strata.rules.roles.helpers.checks import (
    banned_generic_filename,
    banned_generic_package_name,
    classes_module_name,
    helpers_classes_file_private,
    helpers_module_name,
)
from strata.rules.roles.types import RoleCode


def naming_rules() -> tuple[RuleSpec, ...]:
    """Build naming and helper-content role rules."""

    return (
        RuleSpec(
            code=RoleCode.BANNED_GENERIC_FILENAME,
            family=Family.ROLES,
            slug="banned-generic-filename",
            message="generic filenames hide module ownership",
            remediation="Rename the module after the domain concept or operation it owns.",
            check=banned_generic_filename,
        ),
        RuleSpec(
            code=RoleCode.HELPERS_MODULE_NAME,
            family=Family.ROLES,
            slug="helpers-module-name",
            message="use a helpers package instead of helpers.py",
            remediation="Replace helpers.py with a helpers/ package of specifically named modules.",
            check=helpers_module_name,
        ),
        RuleSpec(
            code=RoleCode.CLASSES_MODULE_NAME,
            family=Family.ROLES,
            slug="classes-module-name",
            message="use a classes package instead of classes.py",
            remediation=(
                "Replace classes.py with a classes/ package containing one class per module."
            ),
            check=classes_module_name,
        ),
        RuleSpec(
            code=RoleCode.BANNED_GENERIC_PACKAGE_NAME,
            family=Family.ROLES,
            slug="banned-generic-package-name",
            message="domain and subdomain packages must identify an owner",
            remediation=(
                "Rename the package after the business domain or technical capability it owns."
            ),
            check=banned_generic_package_name,
        ),
        RuleSpec(
            code=RoleCode.HELPERS_CLASSES_FILE_PRIVATE,
            family=Family.ROLES,
            slug="helpers-classes-file-private",
            message="plain classes in helpers modules must be file-private",
            remediation=(
                "Prefix a file-local helper class with _, or move a shared class into classes/."
            ),
            check=helpers_classes_file_private,
        ),
    )
