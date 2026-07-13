"""Inspect expected generated-skill targets without filesystem mutation."""

from __future__ import annotations

import errno
import os
import stat
from pathlib import Path

from strata.agentdocs._helpers.installation import normalization_collision
from strata.agentdocs._helpers.ownership import (
    generated_marker_present,
    parse_skill_ownership,
    skill_content_fingerprint_matches,
)
from strata.agentdocs.models import SkillInstallPlan, SkillOwnership
from strata.agentdocs.types import SkillFreshnessReason


def inspect_skill_content(
    *,
    plan: SkillInstallPlan,
    path: Path,
    expected_content: bytes | None,
) -> SkillFreshnessReason | None:
    """Classify one expected target, or return None when it is current or declined."""

    authoritative: bool = expected_content is not None
    if authoritative and normalization_collision(path) is not None:
        return SkillFreshnessReason.COLLISION
    content, collision = _read_skill_content(path)
    if collision:
        return SkillFreshnessReason.COLLISION if authoritative else None
    if content is None:
        return SkillFreshnessReason.MISSING if authoritative else None
    if not generated_marker_present(content):
        return SkillFreshnessReason.COLLISION if authoritative else None
    ownership: SkillOwnership | None = parse_skill_ownership(content)
    if ownership is None:
        return SkillFreshnessReason.MALFORMED_MARKER if authoritative else None
    if ownership.owner != plan.owner or ownership.identity != plan.context.identity:
        return SkillFreshnessReason.COLLISION if authoritative else None
    if ownership.input_fingerprint != plan.input_fingerprint:
        return SkillFreshnessReason.STALE
    if not skill_content_fingerprint_matches(content=content, ownership=ownership):
        return SkillFreshnessReason.DIVERGENT
    if expected_content is not None and content != expected_content:
        return SkillFreshnessReason.DIVERGENT
    return None


def _read_skill_content(path: Path) -> tuple[bytes | None, bool]:
    try:
        for parent in path.parents:
            if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
                return None, True
        if path.is_symlink():
            return None, True
        flags: int = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NOATIME", 0)
        try:
            descriptor: int = os.open(path, flags)
        except FileNotFoundError:
            return None, False
        except PermissionError as error:
            if error.errno != errno.EPERM or not getattr(os, "O_NOATIME", 0):
                return None, True
            descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        with os.fdopen(descriptor, "rb") as skill_file:
            metadata: os.stat_result = os.fstat(skill_file.fileno())
            if not stat.S_ISREG(metadata.st_mode):
                return None, True
            content: bytes = skill_file.read()
            final_metadata: os.stat_result = os.fstat(skill_file.fileno())
        stable: tuple[int, ...] = (
            metadata.st_dev,
            metadata.st_ino,
            metadata.st_size,
            metadata.st_mtime_ns,
            metadata.st_ctime_ns,
        )
        final: tuple[int, ...] = (
            final_metadata.st_dev,
            final_metadata.st_ino,
            final_metadata.st_size,
            final_metadata.st_mtime_ns,
            final_metadata.st_ctime_ns,
        )
        return (content, False) if stable == final else (None, True)
    except OSError:
        return None, True
