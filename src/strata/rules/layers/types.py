"""Layer rule type declarations."""

from __future__ import annotations

from enum import StrEnum


class LayerCode(StrEnum):
    """Stable diagnostic codes for the layers family."""

    ABSOLUTE_IMPORTS_ONLY = "SFL001"
    NO_SIBLING_PACKAGE_INTERNALS = "SFL101"
    NO_CROSS_PACKAGE_INTERNALS = "SFL102"
    NO_CROSS_FILE_HELPER_PRIVATE_CLASS = "SFL110"
    NO_RUNTIME_IMPORTS_FROM_TOOLING = "SFL301"
