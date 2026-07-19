"""Agent skill generation and installation errors."""

from __future__ import annotations


class SkillInstallError(Exception):
    """Raised when a skill destination cannot be safely updated."""
