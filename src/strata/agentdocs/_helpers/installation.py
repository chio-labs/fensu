"""Resolve agent skill destinations and write generated files safely."""

from __future__ import annotations

import os
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from strata.agentdocs._helpers.ownership import generated_marker_present, parse_skill_ownership
from strata.agentdocs.constants import GENERIC_SKILL_NAME
from strata.agentdocs.exceptions import SkillInstallError
from strata.agentdocs.models import SkillInstallTarget, SkillOwnership
from strata.agentdocs.types import SkillTarget


@dataclass(frozen=True, slots=True)
class _SkillFileSnapshot:
    path: Path
    content: bytes | None
    mode: int | None
    device: int | None
    inode: int | None
    expected_owner: str | None = None


@dataclass(frozen=True, slots=True)
class _StagedSkillFile:
    snapshot: _SkillFileSnapshot
    path: Path


@dataclass(frozen=True, slots=True)
class _PublishedSkillFile:
    original: _SkillFileSnapshot
    installed: _SkillFileSnapshot


@dataclass(frozen=True, slots=True)
class _StagedSkillDeletion:
    snapshot: _SkillFileSnapshot
    backup: Path


@dataclass(frozen=True, slots=True)
class _PublishedSkillDeletion:
    snapshot: _SkillFileSnapshot
    backup: Path
    quarantine: Path


def build_install_targets(
    *,
    install_root: Path,
    skill_name: str,
    requested_targets: tuple[SkillTarget, ...],
    global_install: bool,
    home_dir: Path | None,
) -> tuple[SkillInstallTarget, ...]:
    """Resolve requested or default agent-specific skill paths."""

    target_names: tuple[SkillTarget, ...] = tuple(
        dict.fromkeys(requested_targets or tuple(SkillTarget))
    )
    home_path: Path = home_dir if home_dir is not None else Path.home()
    install_targets: list[SkillInstallTarget] = []
    for target_name in target_names:
        if target_name is SkillTarget.OPENCODE:
            base_path: Path = (
                home_path / ".config/opencode" if global_install else install_root / ".opencode"
            )
        elif target_name is SkillTarget.CLAUDE:
            base_path = home_path / ".claude" if global_install else install_root / ".claude"
        else:
            base_path = home_path / ".agents" if global_install else install_root / ".agents"
        install_targets.append(
            SkillInstallTarget(
                name=target_name,
                path=base_path / "skills" / skill_name / "SKILL.md",
            )
        )
    return tuple(install_targets)


def build_legacy_paths(
    *,
    context_roots: tuple[Path, ...],
    install_targets: tuple[SkillInstallTarget, ...],
    global_install: bool,
) -> tuple[Path, ...]:
    """Return applicable generic skill paths for marker-gated migration."""

    paths: list[Path] = []
    if global_install:
        return tuple(
            target.path.parent.parent / GENERIC_SKILL_NAME / "SKILL.md"
            for target in install_targets
        )
    for root in dict.fromkeys(path.resolve() for path in context_roots):
        for target in install_targets:
            paths.append(
                root
                / target.path.parents[2].name
                / target.path.parents[1].name
                / GENERIC_SKILL_NAME
                / "SKILL.md"
            )
    return tuple(dict.fromkeys(paths))


def validate_skill_file(*, path: Path, force: bool) -> None:
    """Reject unsafe or user-authored destinations unless overwrite is forced."""

    _ = _capture_skill_file(path=path, force=force)


def normalization_collision(path: Path) -> Path | None:
    """Return a case-only sibling collision for one normalized skill path."""

    skill_directory: Path = path.parent
    skills_directory: Path = skill_directory.parent
    if not skills_directory.is_dir():
        return None
    for entry in skills_directory.iterdir():
        if entry.name != skill_directory.name and (
            entry.name.casefold() == skill_directory.name.casefold()
        ):
            return entry
    return None


def write_skill_file(*, path: Path, content: str, force: bool) -> None:
    """Write one generated skill with transactional destination safeguards."""

    write_skill_files(paths=(path,), content=content, force=force)


def write_skill_files(
    *,
    paths: tuple[Path, ...],
    deletion_paths: tuple[Path, ...] = (),
    content: str,
    force: bool,
    owner: str | None = None,
) -> None:
    """Transactionally replace all skill destinations or leave all targets unchanged."""

    try:
        snapshots: tuple[_SkillFileSnapshot, ...] = tuple(
            _capture_skill_file(path=path, force=force, expected_owner=owner) for path in paths
        )
        deletion_snapshots: tuple[_SkillFileSnapshot, ...] = tuple(
            snapshot
            for path in deletion_paths
            if (snapshot := _capture_legacy_file(path=path, owner=owner)) is not None
        )
    except OSError as error:
        raise SkillInstallError(f"failed to inspect skill files: {error}") from error
    staged_files: list[_StagedSkillFile] = []
    staged_deletions: list[_StagedSkillDeletion] = []
    published_files: list[_PublishedSkillFile] = []
    published_deletions: list[_PublishedSkillDeletion] = []
    try:
        for snapshot in snapshots:
            snapshot.path.parent.mkdir(parents=True, exist_ok=True)
            _ensure_unchanged(snapshot=snapshot, force=force)
            staged_path: Path = _stage_content(
                destination=snapshot.path,
                content=content.encode("utf-8"),
                mode=snapshot.mode,
            )
            staged_files.append(_StagedSkillFile(snapshot=snapshot, path=staged_path))
        for snapshot in deletion_snapshots:
            backup: Path = _stage_content(
                destination=snapshot.path,
                content=snapshot.content or b"",
                mode=snapshot.mode,
            )
            staged_deletions.append(_StagedSkillDeletion(snapshot=snapshot, backup=backup))
        for staged_file in staged_files:
            _ensure_unchanged(snapshot=staged_file.snapshot, force=force)
            published_file: _PublishedSkillFile = _publish_staged_file(staged_file=staged_file)
            published_files.append(published_file)
        for staged_deletion in staged_deletions:
            published_deletions.append(_publish_skill_deletion(staged=staged_deletion))
        for published_deletion in published_deletions:
            published_deletion.quarantine.unlink()
    except SkillInstallError:
        _rollback_skill_deletions(published_deletions=published_deletions)
        _rollback_skill_files(published_files=published_files)
        raise
    except OSError as error:
        _rollback_skill_deletions(published_deletions=published_deletions)
        _rollback_skill_files(published_files=published_files)
        raise SkillInstallError(f"failed to install skill files: {error}") from error
    finally:
        for staged_file in staged_files:
            staged_file.path.unlink(missing_ok=True)
        for staged_deletion in staged_deletions:
            staged_deletion.backup.unlink(missing_ok=True)
    for snapshot in deletion_snapshots:
        try:
            snapshot.path.parent.rmdir()
        except OSError:
            pass


def _capture_skill_file(
    *, path: Path, force: bool, expected_owner: str | None = None
) -> _SkillFileSnapshot:
    if expected_owner is not None:
        _validate_normalization_collision(path)
    if path.is_symlink():
        raise SkillInstallError(f"refusing to write unsafe skill target: {path}")
    for parent in path.parents:
        if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
            raise SkillInstallError(f"refusing to write unsafe skill target: {path}")
    if not path.exists():
        return _SkillFileSnapshot(
            path=path,
            content=None,
            mode=None,
            device=None,
            inode=None,
            expected_owner=expected_owner,
        )
    descriptor: int = os.open(
        path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
    )
    with os.fdopen(descriptor, "rb") as existing_file:
        metadata: os.stat_result = os.fstat(existing_file.fileno())
        if not stat.S_ISREG(metadata.st_mode):
            raise SkillInstallError(f"refusing to write unsafe skill target: {path}")
        existing_content: bytes = existing_file.read()
        final_metadata: os.stat_result = os.fstat(existing_file.fileno())
    path_metadata: os.stat_result = path.stat(follow_symlinks=False)
    stable_file_state: tuple[int, ...] = (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )
    final_file_state: tuple[int, ...] = (
        final_metadata.st_dev,
        final_metadata.st_ino,
        final_metadata.st_mode,
        final_metadata.st_size,
        final_metadata.st_mtime_ns,
        final_metadata.st_ctime_ns,
    )
    if stable_file_state != final_file_state or (
        path_metadata.st_dev,
        path_metadata.st_ino,
    ) != (final_metadata.st_dev, final_metadata.st_ino):
        raise SkillInstallError(f"skill target changed during update: {path}")
    ownership: SkillOwnership | None = parse_skill_ownership(existing_content)
    foreign_owner: bool = (
        ownership is not None
        and expected_owner is not None
        and (ownership.owner != expected_owner or ownership.identity != path.parent.name)
    )
    if foreign_owner:
        raise SkillInstallError(
            f"refusing to overwrite skill owned by another Strata project: {path}"
        )
    if expected_owner is not None and ownership is None and not force:
        raise SkillInstallError(
            f"refusing to overwrite unmanaged skill file: {path}; rerun with --force"
        )
    if expected_owner is None and not generated_marker_present(existing_content) and not force:
        raise SkillInstallError(
            f"refusing to overwrite non-generated skill file: {path}; rerun with --force"
        )
    return _SkillFileSnapshot(
        path=path,
        content=existing_content,
        mode=stat.S_IMODE(final_metadata.st_mode),
        device=final_metadata.st_dev,
        inode=final_metadata.st_ino,
        expected_owner=expected_owner,
    )


def _ensure_unchanged(*, snapshot: _SkillFileSnapshot, force: bool) -> None:
    current: _SkillFileSnapshot = _capture_skill_file(
        path=snapshot.path,
        force=force,
        expected_owner=snapshot.expected_owner,
    )
    if current != snapshot:
        raise SkillInstallError(f"skill target changed during update: {snapshot.path}")


def _stage_content(*, destination: Path, content: bytes, mode: int | None) -> Path:
    descriptor: int
    temporary_name: str
    descriptor, temporary_name = tempfile.mkstemp(prefix=".strata-skill-", dir=destination.parent)
    staged_path: Path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as staged_file:
            _ = staged_file.write(content)
            staged_file.flush()
            os.fsync(staged_file.fileno())
        staged_path.chmod(0o644 if mode is None else mode)
    except OSError:
        staged_path.unlink(missing_ok=True)
        raise
    return staged_path


def _publish_staged_file(*, staged_file: _StagedSkillFile) -> _PublishedSkillFile:
    snapshot: _SkillFileSnapshot = staged_file.snapshot
    if snapshot.content is None:
        os.link(staged_file.path, snapshot.path, follow_symlinks=False)
    else:
        _publish_existing_skill(staged_path=staged_file.path, snapshot=snapshot)
    installed: _SkillFileSnapshot = _capture_skill_file(
        path=snapshot.path,
        force=True,
        expected_owner=snapshot.expected_owner,
    )
    return _PublishedSkillFile(original=snapshot, installed=installed)


def _publish_existing_skill(*, staged_path: Path, snapshot: _SkillFileSnapshot) -> None:
    installed_content: bytes = staged_path.read_bytes()
    descriptor: int = os.open(
        snapshot.path,
        os.O_RDWR | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0),
    )
    with os.fdopen(descriptor, "r+b") as target_file:
        _validate_open_skill_file(target_file=target_file, snapshot=snapshot)
        _write_skill_descriptor(target_file=target_file, content=installed_content)
    current: _SkillFileSnapshot = _capture_skill_file(
        path=snapshot.path,
        force=True,
        expected_owner=snapshot.expected_owner,
    )
    if (
        current.device != snapshot.device
        or current.inode != snapshot.inode
        or current.content != installed_content
    ):
        raise SkillInstallError(f"skill target changed during update: {snapshot.path}")


def _validate_open_skill_file(*, target_file: BinaryIO, snapshot: _SkillFileSnapshot) -> None:
    metadata: os.stat_result = os.fstat(target_file.fileno())
    target_file.seek(0)
    current_content: bytes = target_file.read()
    if (
        metadata.st_dev != snapshot.device
        or metadata.st_ino != snapshot.inode
        or stat.S_IMODE(metadata.st_mode) != snapshot.mode
        or current_content != snapshot.content
    ):
        raise SkillInstallError(f"skill target changed during update: {snapshot.path}")


def _write_skill_descriptor(*, target_file: BinaryIO, content: bytes) -> None:
    target_file.seek(0)
    _ = target_file.write(content)
    target_file.truncate()
    target_file.flush()
    os.fsync(target_file.fileno())


def _rollback_skill_files(*, published_files: list[_PublishedSkillFile]) -> None:
    for published_file in reversed(published_files):
        try:
            current: _SkillFileSnapshot = _capture_skill_file(
                path=published_file.installed.path,
                force=True,
                expected_owner=None,
            )
            if not _same_file_snapshot(first=current, second=published_file.installed):
                continue
            if published_file.original.content is None:
                current.path.unlink()
            else:
                _restore_existing_skill(published_file=published_file)
        except (OSError, SkillInstallError):
            continue


def _restore_existing_skill(*, published_file: _PublishedSkillFile) -> None:
    descriptor: int = os.open(
        published_file.installed.path,
        os.O_RDWR | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0),
    )
    with os.fdopen(descriptor, "r+b") as target_file:
        _validate_open_skill_file(
            target_file=target_file,
            snapshot=published_file.installed,
        )
        original_content: bytes | None = published_file.original.content
        if original_content is not None:
            _write_skill_descriptor(target_file=target_file, content=original_content)


def _capture_legacy_file(*, path: Path, owner: str | None) -> _SkillFileSnapshot | None:
    snapshot: _SkillFileSnapshot = _capture_skill_file(path=path, force=True)
    if snapshot.content is None or not generated_marker_present(snapshot.content):
        return None
    ownership: SkillOwnership | None = parse_skill_ownership(snapshot.content)
    if ownership is not None and ownership.owner != owner:
        return None
    return snapshot


def _validate_normalization_collision(path: Path) -> None:
    collision: Path | None = normalization_collision(path)
    if collision is not None:
        raise SkillInstallError(
            f"skill identity normalization collides with existing path: {collision}"
        )


def _publish_skill_deletion(*, staged: _StagedSkillDeletion) -> _PublishedSkillDeletion:
    _ensure_unchanged(snapshot=staged.snapshot, force=True)
    descriptor: int
    temporary_name: str
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".strata-legacy-", dir=staged.snapshot.path.parent
    )
    os.close(descriptor)
    quarantine: Path = Path(temporary_name)
    quarantine.unlink()
    try:
        staged.snapshot.path.rename(quarantine)
        moved: _SkillFileSnapshot = _capture_skill_file(path=quarantine, force=True)
        if not _same_file_snapshot(first=staged.snapshot, second=moved):
            quarantine.rename(staged.snapshot.path)
            raise SkillInstallError(
                f"legacy skill target changed during migration: {staged.snapshot.path}"
            )
    except (OSError, SkillInstallError):
        if quarantine.exists() and not staged.snapshot.path.exists():
            quarantine.rename(staged.snapshot.path)
        raise
    return _PublishedSkillDeletion(
        snapshot=staged.snapshot,
        backup=staged.backup,
        quarantine=quarantine,
    )


def _same_file_snapshot(*, first: _SkillFileSnapshot, second: _SkillFileSnapshot) -> bool:
    return (
        first.content == second.content
        and first.mode == second.mode
        and first.device == second.device
        and first.inode == second.inode
    )


def _rollback_skill_deletions(*, published_deletions: list[_PublishedSkillDeletion]) -> None:
    for deletion in reversed(published_deletions):
        try:
            if deletion.snapshot.path.exists() or deletion.snapshot.path.is_symlink():
                continue
            if deletion.quarantine.exists():
                deletion.quarantine.rename(deletion.snapshot.path)
            else:
                os.link(deletion.backup, deletion.snapshot.path, follow_symlinks=False)
                if deletion.snapshot.mode is not None:
                    deletion.snapshot.path.chmod(deletion.snapshot.mode)
        except OSError:
            continue
