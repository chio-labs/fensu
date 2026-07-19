"""Layer import-boundary rule catalogue entries."""

from __future__ import annotations

from fensu.rules.authoring.models import RuleSpec
from fensu.rules.authoring.types import ExecutionOwner, Family
from fensu.rules.layers._helpers.checks import (
    absolute_imports_only,
    no_cross_domain_private_main_imports,
    no_cross_package_internals,
    no_internal_public_surface_imports,
    no_runtime_imports_from_tooling,
    no_sibling_package_internals,
    no_star_imports,
    public_main_entry_external_use,
)
from fensu.rules.layers.types import LayerCode


def import_rules() -> tuple[RuleSpec, ...]:
    """Build import-boundary layer rules."""

    return (
        RuleSpec(
            code=LayerCode.ABSOLUTE_IMPORTS_ONLY,
            family=Family.LAYERS,
            slug="absolute-imports-only",
            message="use absolute imports; relative imports hide package boundaries",
            remediation="Replace relative imports with an absolute import path.",
            check=absolute_imports_only,
        ),
        RuleSpec(
            code=LayerCode.NO_STAR_IMPORTS,
            family=Family.LAYERS,
            slug="no-star-imports",
            message="star imports hide names from dependency-boundary analysis",
            remediation="Import each required name explicitly.",
            check=no_star_imports,
        ),
        RuleSpec(
            code=LayerCode.NO_SIBLING_PACKAGE_INTERNALS,
            family=Family.LAYERS,
            slug="no-sibling-package-internals",
            message="subpackage code must not import sibling internals",
            remediation=(
                "Publish the dependency through the owning sibling's main/ entry or role files."
            ),
            check=no_sibling_package_internals,
        ),
        RuleSpec(
            code=LayerCode.NO_CROSS_PACKAGE_INTERNALS,
            family=Family.LAYERS,
            slug="no-cross-package-internals",
            message="cross-package imports must use public surfaces, not helpers or internals",
            remediation=(
                "Import from classes, models, types, constants, exceptions, or a thin main/ entry."
            ),
            check=no_cross_package_internals,
        ),
        RuleSpec(
            code=LayerCode.NO_INTERNAL_PUBLIC_SURFACE_IMPORTS,
            family=Family.LAYERS,
            slug="no-internal-public-surface-imports",
            message="internal code must import from the owning module, not the bare package",
            remediation="Import from the concrete owning module below the package surface.",
            check=no_internal_public_surface_imports,
        ),
        RuleSpec(
            code=LayerCode.NO_CROSS_DOMAIN_PRIVATE_MAIN_IMPORTS,
            family=Family.LAYERS,
            slug="no-cross-domain-private-main-imports",
            message="domain-private main entries may only be imported within their owning domain",
            remediation=(
                "Remove the leading underscore to publish the main entry, or route the caller "
                "through a public main entry owned by the target domain."
            ),
            check=no_cross_domain_private_main_imports,
        ),
        RuleSpec(
            code=LayerCode.PUBLIC_MAIN_ENTRY_EXTERNAL_USE,
            family=Family.LAYERS,
            slug="public-main-entry-external-use",
            message="public main entries must have an importer outside their owning domain",
            remediation=(
                "Prefix the entry module filename with '_' until another domain or tooling "
                "imports it."
            ),
            check=public_main_entry_external_use,
            execution_owner=ExecutionOwner.PROJECT,
        ),
        RuleSpec(
            code=LayerCode.NO_RUNTIME_IMPORTS_FROM_TOOLING,
            family=Family.LAYERS,
            slug="no-runtime-imports-from-tooling",
            message="runtime code must not import from tooling modules",
            remediation=(
                "Move reusable logic into the runtime package or keep the dependency inside "
                "tooling."
            ),
            check=no_runtime_imports_from_tooling,
        ),
    )
