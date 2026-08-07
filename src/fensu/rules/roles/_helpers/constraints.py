"""Fixed exhaustive value sets for role rules."""

from __future__ import annotations

from fensu.rules.authoring.models import RuleConstraint
from fensu.rules.roles.types import RoleCode


def get_role_rule_constraints(code: RoleCode) -> tuple[RuleConstraint, ...]:
    """Return fixed constraints owned by one role rule."""

    constraints: dict[RoleCode, tuple[RuleConstraint, ...]] = {
        RoleCode.HELPERS_PACKAGE_LAYOUT: (_forbidden_bucket_names(),),
        RoleCode.MAIN_PACKAGE_LAYOUT: (_forbidden_bucket_names(),),
        RoleCode.HELPERS_RESERVED_ROLE_FILENAMES: (_reserved_role_filenames(),),
        RoleCode.NESTED_DIRECT_MODULES: (
            _recognized_role_directories(),
            _recognized_role_filenames(),
        ),
        RoleCode.NESTED_DIRECT_SUBPACKAGES: (_recognized_role_directories(),),
        RoleCode.TOP_LEVEL_DIRECT_MODULES: (_recognized_role_filenames(),),
        RoleCode.TYPE_DECLARATION_OUTSIDE_TYPES: (
            RuleConstraint(
                name="allowed_private_type_roles",
                description="Roles allowed to own private type declarations",
                values=("helpers",),
            ),
        ),
        RoleCode.NO_REEXPORT_SHIM: (
            RuleConstraint(
                name="exempt_roles",
                description="Roles exempt from the pure re-export shim rule",
                values=("exceptions",),
            ),
        ),
        RoleCode.TOOLING_ENTRYPOINT_SHAPE: (
            RuleConstraint(
                name="allowed_command_functions",
                description="Allowed direct-script command functions",
                values=("main", "_parse_args", "_build_parser"),
            ),
            RuleConstraint(
                name="allowed_top_level_statement_kinds",
                description="Allowed direct-script top-level statement kinds",
                values=("import statement", "command function", "nonexecuting import guard"),
            ),
        ),
        RoleCode.TOOLING_ENTRYPOINT_DELEGATION: (
            RuleConstraint(
                name="allowed_local_main_call_targets",
                description="Allowed local direct-script main() call targets",
                values=("_parse_args",),
            ),
            RuleConstraint(
                name="allowed_imported_entry_roles",
                description="Roles whose imported entries may be called by direct-script main()",
                values=("main",),
            ),
        ),
        RoleCode.TOOLING_PACKAGE_LAYOUT: (
            RuleConstraint(
                name="allowed_tooling_role_directories",
                description="Allowed tooling role directories",
                values=("main", "_helpers", "classes", "rules"),
            ),
            RuleConstraint(
                name="allowed_tooling_role_files",
                description="Allowed tooling role files",
                values=("models.py", "types.py", "constants.py", "exceptions.py"),
            ),
        ),
    }
    return constraints.get(code, ())


def _forbidden_bucket_names() -> RuleConstraint:
    return RuleConstraint(
        name="forbidden_bucket_names",
        description="Forbidden role bucket names",
        values=(
            "main",
            "_helpers",
            "helpers",
            "classes",
            "models",
            "types",
            "constants",
            "exceptions",
        ),
    )


def _reserved_role_filenames() -> RuleConstraint:
    return RuleConstraint(
        name="reserved_role_filenames",
        description="Reserved role filenames",
        values=("models.py", "types.py", "constants.py", "exceptions.py"),
    )


def _recognized_role_directories() -> RuleConstraint:
    return RuleConstraint(
        name="recognized_role_directories",
        description="Recognized runtime role directories",
        values=("main", "_helpers", "classes", "models", "types", "constants", "exceptions"),
    )


def _recognized_role_filenames() -> RuleConstraint:
    return RuleConstraint(
        name="recognized_role_filenames",
        description="Recognized runtime role filenames",
        values=(
            "main.py",
            "helpers.py",
            "classes.py",
            "models.py",
            "types.py",
            "constants.py",
            "exceptions.py",
        ),
    )
