"""Configuration type-layer declarations."""

from __future__ import annotations

from enum import StrEnum


class ConfigSourceKind(StrEnum):
    """Supported configuration source formats."""

    STRATA_TOML = "strata_toml"
    PYPROJECT = "pyproject"


class RuleSelector(StrEnum):
    """Built-in rule selection prefixes."""

    ALL = "SF"
    LAYERS = "SFL"
    ROLES = "SFR"
    SHAPE = "SFS"
    NAMING = "SFN"
    HYGIENE = "SFX"
    TESTS = "SFT"
    ANNOTATIONS = "SFA"


class ContractBehavior(StrEnum):
    """Supported function-name contract behaviors."""

    NO_RETURN = "no-return"
