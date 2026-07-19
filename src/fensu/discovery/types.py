"""Discovery type-layer declarations."""

from __future__ import annotations

from enum import StrEnum


class ScopeName(StrEnum):
    """Configured repository scan scopes."""

    ROOT = "root"
    TEST = "test"
    TOOLING = "tooling"


class RoleName(StrEnum):
    """Standard module and package roles."""

    CLASSES = "classes"
    CONSTANTS = "constants"
    ENTRY = "entry"
    EXCEPTIONS = "exceptions"
    HELPERS = "helpers"
    MAIN = "main"
    MODELS = "models"
    RULES = "rules"
    TYPES = "types"
