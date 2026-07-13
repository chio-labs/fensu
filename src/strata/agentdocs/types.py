"""Agent skill type-layer declarations."""

from __future__ import annotations

from enum import StrEnum


class SkillCommand(StrEnum):
    """Supported skills subcommands."""

    UPDATE = "update"


class SkillTarget(StrEnum):
    """Supported agent skill installation targets."""

    OPENCODE = "opencode"
    CLAUDE = "claude"
    AGENTS = "agents"


class SkillInstallRoot(StrEnum):
    """Named local skill installation roots."""

    GIT = "git"
    PROJECT = "project"


class SkillFreshnessReason(StrEnum):
    """Deterministic reasons an expected skill installation is not current."""

    STALE = "stale"
    MISSING = "missing"
    DIVERGENT = "divergent"
    MALFORMED_MARKER = "malformed-marker"
    COLLISION = "collision"
