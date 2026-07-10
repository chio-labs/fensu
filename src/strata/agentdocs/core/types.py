"""Agent skill type-layer declarations."""

from __future__ import annotations

from enum import StrEnum


class SkillTarget(StrEnum):
    """Supported agent skill installation targets."""

    OPENCODE = "opencode"
    CLAUDE = "claude"
    AGENTS = "agents"
