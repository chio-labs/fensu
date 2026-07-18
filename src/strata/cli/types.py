"""CLI type-layer declarations."""

from __future__ import annotations

from enum import StrEnum


class CliCommand(StrEnum):
    """Supported top-level CLI commands."""

    CHECK = "check"
    INIT = "init"
    RULE = "rule"
    SKILLS = "skills"
    MAP = "map"
    MEMORY = "memory"


class CliOption(StrEnum):
    """Supported top-level CLI options."""

    HELP = "--help"
    SHORT_HELP = "-h"
    VERSION = "--version"


class ColorMode(StrEnum):
    """Supported terminal color modes."""

    AUTO = "auto"
    ALWAYS = "always"
    NEVER = "never"


class MemoryCliCommand(StrEnum):
    """Supported Strata Memory subcommands."""

    ARCHIVE = "archive"
    CHECK = "check"
    SYNC = "sync"
    REBUILD = "rebuild"
    SCHEMA = "schema"
    SQL = "sql"
