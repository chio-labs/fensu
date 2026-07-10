"""CLI type-layer declarations."""

from __future__ import annotations

from enum import StrEnum


class CliCommand(StrEnum):
    """Supported top-level CLI commands."""

    CHECK = "check"
    RULE = "rule"
    SKILL = "skill"
    MAP = "map"


class ColorMode(StrEnum):
    """Supported terminal color modes."""

    AUTO = "auto"
    ALWAYS = "always"
    NEVER = "never"
