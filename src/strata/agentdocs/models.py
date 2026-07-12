"""Agent skill installation models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from strata.agentdocs.types import SkillTarget


@dataclass(frozen=True, slots=True)
class SkillInstallTarget:
    """One agent-specific skill destination."""

    name: SkillTarget
    path: Path


@dataclass(frozen=True, slots=True)
class SkillUpdateResult:
    """Files written by one skills update."""

    written_paths: tuple[Path, ...]
