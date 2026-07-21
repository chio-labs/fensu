"""Role naming and helper-content rule catalogue entries."""

from __future__ import annotations

from fensu.rules.authoring.models import RuleSpec
from fensu.rules.authoring.types import Family
from fensu.rules.roles.types import RoleCode


def naming_rules() -> tuple[RuleSpec, ...]:
    """Build naming and helper-content role rules."""

    return (
        RuleSpec(
            code=RoleCode.BANNED_GENERIC_FILENAME,
            family=Family.ROLES,
            slug="banned-generic-filename",
            message="generic filenames hide module ownership",
            remediation="Rename the module after the domain concept or operation it owns.",
        ),
        RuleSpec(
            code=RoleCode.HELPERS_MODULE_NAME,
            family=Family.ROLES,
            slug="helpers-module-name",
            message="use an _helpers package instead of helpers.py",
            remediation=(
                "Replace helpers.py with an _helpers/ package of specifically named modules."
            ),
        ),
        RuleSpec(
            code=RoleCode.CLASSES_MODULE_NAME,
            family=Family.ROLES,
            slug="classes-module-name",
            message="use a classes package instead of classes.py",
            remediation=(
                "Replace classes.py with a classes/ package containing one class per module."
            ),
        ),
        RuleSpec(
            code=RoleCode.BANNED_GENERIC_PACKAGE_NAME,
            family=Family.ROLES,
            slug="banned-generic-package-name",
            message="runtime package directories must identify an owner",
            remediation=(
                "Rename the package after the business domain or technical capability it owns."
            ),
        ),
        RuleSpec(
            code=RoleCode.HELPERS_CLASSES_FILE_PRIVATE,
            family=Family.ROLES,
            slug="helpers-classes-file-private",
            message="plain classes in _helpers modules must be file-private",
            remediation=(
                "Prefix a file-local helper class with _, or move a shared class into classes/."
            ),
        ),
    )
