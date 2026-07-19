"""Configuration type-layer declarations."""

from __future__ import annotations

from enum import StrEnum


class ConfigSourceKind(StrEnum):
    """Supported configuration source formats."""

    FENSU_TOML = "fensu_toml"
    PYPROJECT = "pyproject"


class RuleSelector(StrEnum):
    """Built-in rule selection prefixes."""

    ALL = "FF"
    LAYERS = "FFL"
    ROLES = "FFR"
    SHAPE = "FFS"
    NAMING = "FFN"
    HYGIENE = "FFH"
    TESTS = "FFT"
    ANNOTATIONS = "FFA"
    CUSTOM = "X"


class ContractBehavior(StrEnum):
    """Supported function-name contract behaviors."""

    NO_RETURN = "no-return"
    RETURNS_BOOL = "returns-bool"
    RETURNS_VALUE = "returns-value"
    RETURNS_ITERATOR = "returns-iterator"
