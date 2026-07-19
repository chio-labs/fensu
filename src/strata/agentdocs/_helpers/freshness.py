"""Inspect expected generated-skill targets without filesystem mutation."""

from __future__ import annotations

import errno
import os
import stat
from pathlib import Path

from strata.agentdocs._helpers.installation import normalization_collision
from strata.agentdocs._helpers.ownership import (
    generated_marker_present,
    owned_project_skill_content,
    parse_skill_ownership,
    project_skill_input_fingerprint,
    project_skill_marker_present,
    skill_content_fingerprint_matches,
)
from strata.agentdocs.models import (
    ProjectSkillInstallTarget,
    SkillFreshnessIssue,
    SkillInstallPlan,
    SkillOwnership,
)
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


def inspect_project_skill_install(plan: SkillInstallPlan) -> tuple[SkillFreshnessIssue, ...]:
    """Inspect complete selected project bundles and owned stale copies without writes."""

    issues: list[SkillFreshnessIssue] = []
    desired_by_directory: dict[Path, set[str]] = {}
    for generated_target in plan.targets:
        desired_by_directory.setdefault(generated_target.path.parent.parent, set()).add(
            plan.context.identity.casefold()
        )
    for target in sorted(plan.project_targets, key=lambda item: item.path.as_posix()):
        desired_by_directory.setdefault(target.path.parent, set()).add(
            target.bundle.identity.casefold()
        )
        issues.extend(_inspect_project_target(plan=plan, target=target))
    if plan.synchronize_project_skills:
        issues.extend(
            _inspect_stale_project_targets(plan=plan, desired_by_directory=desired_by_directory)
        )
    return tuple(sorted(issues, key=lambda issue: issue.path.as_posix()))


def _inspect_project_target(
    *, plan: SkillInstallPlan, target: ProjectSkillInstallTarget
) -> tuple[SkillFreshnessIssue, ...]:
    document_path: Path = target.path / "SKILL.md"
    if normalization_collision(document_path) is not None:
        return (SkillFreshnessIssue(path=document_path, reason=SkillFreshnessReason.COLLISION),)
    installed_paths, unsafe = _read_bundle_paths(target.path)
    if unsafe:
        return (SkillFreshnessIssue(path=document_path, reason=SkillFreshnessReason.COLLISION),)
    if target.path.exists() and document_path not in installed_paths:
        return (SkillFreshnessIssue(path=document_path, reason=SkillFreshnessReason.COLLISION),)
    expected_document: bytes = owned_project_skill_content(
        context=plan.context, bundle=target.bundle
    )
    expected_paths: set[Path] = set()
    issues: list[SkillFreshnessIssue] = []
    input_fingerprint: str = project_skill_input_fingerprint(
        context=plan.context, bundle=target.bundle
    )
    for source_file in target.bundle.files:
        path: Path = target.path / source_file.relative_path
        expected_paths.add(path)
        content, collision = _read_skill_content(path)
        if collision:
            issues.append(SkillFreshnessIssue(path=path, reason=SkillFreshnessReason.COLLISION))
            continue
        if content is None:
            issues.append(SkillFreshnessIssue(path=path, reason=SkillFreshnessReason.MISSING))
            continue
        expected: bytes = (
            expected_document
            if source_file.relative_path == Path("SKILL.md")
            else source_file.content
        )
        if source_file.relative_path == Path("SKILL.md"):
            reason: SkillFreshnessReason | None = _project_document_reason(
                plan=plan,
                target=target,
                content=content,
                expected=expected,
                input_fingerprint=input_fingerprint,
            )
            if reason is not None:
                issues.append(SkillFreshnessIssue(path=path, reason=reason))
            elif stat.S_IMODE(path.stat(follow_symlinks=False).st_mode) != source_file.mode:
                issues.append(SkillFreshnessIssue(path=path, reason=SkillFreshnessReason.DIVERGENT))
        elif content != expected:
            issues.append(SkillFreshnessIssue(path=path, reason=SkillFreshnessReason.DIVERGENT))
        elif stat.S_IMODE(path.stat(follow_symlinks=False).st_mode) != source_file.mode:
            issues.append(SkillFreshnessIssue(path=path, reason=SkillFreshnessReason.DIVERGENT))
    for extra in installed_paths - expected_paths:
        issues.append(SkillFreshnessIssue(path=extra, reason=SkillFreshnessReason.DIVERGENT))
    return tuple(issues)


def _project_document_reason(
    *,
    plan: SkillInstallPlan,
    target: ProjectSkillInstallTarget,
    content: bytes,
    expected: bytes,
    input_fingerprint: str,
) -> SkillFreshnessReason | None:
    if not project_skill_marker_present(content):
        return SkillFreshnessReason.COLLISION
    ownership: SkillOwnership | None = parse_skill_ownership(content)
    if ownership is None:
        return SkillFreshnessReason.MALFORMED_MARKER
    if ownership.owner != plan.owner or ownership.identity != target.bundle.identity:
        return SkillFreshnessReason.COLLISION
    if ownership.input_fingerprint != input_fingerprint:
        return SkillFreshnessReason.STALE
    if not skill_content_fingerprint_matches(content=content, ownership=ownership):
        return SkillFreshnessReason.DIVERGENT
    return None if content == expected else SkillFreshnessReason.DIVERGENT


def _read_bundle_paths(root: Path) -> tuple[set[Path], bool]:
    for parent in root.parents:
        if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
            return set(), True
    if not root.exists():
        return set(), root.is_symlink()
    if root.is_symlink() or not root.is_dir():
        return set(), True
    pending: list[Path] = [root]
    files: set[Path] = set()
    normalized: set[str] = set()
    while pending:
        directory: Path = pending.pop()
        try:
            entries: tuple[Path, ...] = tuple(directory.iterdir())
        except OSError:
            return set(), True
        for entry in entries:
            key: str = entry.relative_to(root).as_posix().casefold()
            if key in normalized or entry.is_symlink():
                return set(), True
            normalized.add(key)
            if entry.is_dir():
                pending.append(entry)
            elif entry.is_file():
                files.add(entry)
            else:
                return set(), True
    return files, False


def _inspect_stale_project_targets(
    *, plan: SkillInstallPlan, desired_by_directory: dict[Path, set[str]]
) -> tuple[SkillFreshnessIssue, ...]:
    issues: list[SkillFreshnessIssue] = []
    for skills_directory, desired in desired_by_directory.items():
        if not skills_directory.is_dir() or skills_directory.is_symlink():
            continue
        for entry in skills_directory.iterdir():
            if entry.name.casefold() in desired or entry.is_symlink() or not entry.is_dir():
                continue
            document: Path = entry / "SKILL.md"
            content, collision = _read_skill_content(document)
            if collision or content is None or not project_skill_marker_present(content):
                continue
            ownership: SkillOwnership | None = parse_skill_ownership(content)
            if (
                ownership is not None
                and ownership.owner == plan.owner
                and ownership.identity == entry.name
            ):
                issues.append(SkillFreshnessIssue(path=document, reason=SkillFreshnessReason.STALE))
    return tuple(issues)


def _read_skill_content(path: Path) -> tuple[bytes | None, bool]:
    try:
        for parent in path.parents:
            if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
                return None, True
        if path.is_symlink():
            return None, True
        flags: int = (
            os.O_RDONLY
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_NOATIME", 0)
            | getattr(os, "O_BINARY", 0)
        )
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
