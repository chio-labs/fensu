"""Actionable catalogue metadata for role layout and surface rules."""

from __future__ import annotations

from strata.rules.roles.types import RoleCode


def role_rule_details(code: RoleCode) -> tuple[str, str]:
    """Return the contract and normal correction for one structural role rule."""

    details: dict[RoleCode, tuple[str, str]] = {
        RoleCode.HELPERS_PACKAGE_LAYOUT: (
            "_helpers/ packages must use bounded flat-or-grouped containers",
            "Keep _helpers/ flat or group every module into bounded shallow buckets; do not mix "
            "modules and Python-containing buckets in one container.",
        ),
        RoleCode.MAIN_PACKAGE_LAYOUT: (
            "main/ packages must use bounded flat-or-grouped orchestration containers",
            "Keep main/ flat or group every entry into bounded shallow buckets; do not mix "
            "modules and Python-containing buckets in one container.",
        ),
        RoleCode.NESTED_DIRECT_MODULES: (
            "nested runtime packages may contain only role-oriented direct modules",
            "Move additional implementation modules under the package's _helpers/ boundary.",
        ),
        RoleCode.NESTED_DIRECT_SUBPACKAGES: (
            "nested runtime packages must use explicit role boundaries",
            "Move feature subpackages under _helpers/ or use a supported role such as main/ or "
            "classes/.",
        ),
        RoleCode.TOP_LEVEL_DOMAIN_SHAPE: (
            "top-level domains must be either role leaves or subdomain branches",
            "Keep direct role content in a leaf domain, or move it into a named subdomain when "
            "the domain contains subdomains.",
        ),
        RoleCode.TOP_LEVEL_DIRECT_MODULES: (
            "top-level domains must not contain ad hoc direct modules",
            "Move the module under a direct role boundary or into an owning named subdomain.",
        ),
        RoleCode.ENTRY_MODULE_SHAPE: (
            "main/ entry modules must expose one focused public function",
            "Keep only imports, one public entry function, and at most two small private glue "
            "functions; move phase logic to _helpers/.",
        ),
        RoleCode.INIT_MODULE_EMPTY: (
            "nested __init__.py files must be empty or docstring-only",
            "Remove runtime declarations and import from the concrete owning module instead.",
        ),
        RoleCode.NO_REEXPORT_SHIM: (
            "internal modules must not exist only to re-export imports",
            "Import the implementation module directly or expose a deliberate API through an "
            "approved public surface.",
        ),
        RoleCode.NO_INTERNAL_HELPER_EXPORTS: (
            "_helpers/ modules must not publish an __all__ surface",
            "Keep _helpers/ internal and expose public behavior through main/, classes/, models, "
            "types, constants, or exceptions.",
        ),
        RoleCode.MAIN_ENTRY_NAME_COLLISION: (
            "main/ cannot define a module and package with the same entry name",
            "Choose either the flat entry module or the same-named package and remove the "
            "competing surface.",
        ),
        RoleCode.PUBLIC_SURFACE_SHAPE: (
            "root package surfaces may contain only imports and one __all__ declaration",
            "Move runtime behavior into an owning module and keep the root __init__.py as a "
            "deliberate import surface.",
        ),
        RoleCode.CLASSES_ONE_CLASS_PER_MODULE: (
            "classes/ modules must define exactly one top-level class",
            "Split additional classes into separately named modules under classes/.",
        ),
        RoleCode.HELPERS_PACKAGE_SHAPE: (
            "_helpers/ packages must contain no main.py orchestration entrypoints",
            "Move main.py orchestration into the sibling main/ role; helper depth is enforced by "
            "SFR301.",
        ),
        RoleCode.PRIVATE_DEFINITION_ORDERING: (
            "private constants and dataclasses must appear before top-level functions",
            "Move private module declarations above the first function so readers see module "
            "state before behavior.",
        ),
        RoleCode.SOURCE_FILE_LINE_COUNT: (
            "source files must stay below the configured line limit",
            "Split the file by a cohesive role or concern instead of extracting arbitrary "
            "numbered fragments.",
        ),
    }
    return details[code]
