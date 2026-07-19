"""Layer rule type declarations."""

from __future__ import annotations

from enum import StrEnum


class LayerCode(StrEnum):
    """Stable diagnostic codes for the layers family."""

    ABSOLUTE_IMPORTS_ONLY = "FFL001"
    NO_STAR_IMPORTS = "FFL002"
    NO_SIBLING_PACKAGE_INTERNALS = "FFL101"
    NO_CROSS_PACKAGE_INTERNALS = "FFL102"
    NO_INTERNAL_PUBLIC_SURFACE_IMPORTS = "FFL103"
    NO_CROSS_DOMAIN_PRIVATE_MAIN_IMPORTS = "FFL104"
    PUBLIC_MAIN_ENTRY_EXTERNAL_USE = "FFL105"
    NO_CROSS_FILE_HELPER_PRIVATE_CLASS = "FFL110"
    NO_RUNTIME_IMPORTS_FROM_TOOLING = "FFL301"
