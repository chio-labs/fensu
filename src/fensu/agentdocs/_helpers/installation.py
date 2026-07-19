"""Discover, resolve, and transactionally synchronize agent skill bundles."""

from __future__ import annotations

import os
import re
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from fensu.agentdocs._helpers.ownership import (
    generated_marker_present,
    owned_project_skill_content,
    parse_skill_ownership,
    project_skill_marker_present,
)
from fensu.agentdocs.constants import (
    GENERIC_SKILL_NAME,
    OWNERSHIP_MARKER_PREFIX,
    PROJECT_SKILL_MARKER,
    PROJECT_SKILLS_RELATIVE_PATH,
    WINDOWS_RESERVED_SKILL_NAMES,
)
from fensu.agentdocs.exceptions import SkillInstallError
from fensu.agentdocs.models import (
    ProjectSkillBundle,
    ProjectSkillFile,
    SkillInstallPlan,
    SkillInstallTarget,
    SkillOwnership,
)
from fensu.agentdocs.types import SkillTarget


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
class _SkillFilePublication:
    snapshot: _SkillFileSnapshot
    content: bytes
    mode: int | None


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


def discover_canonical_project_skills(
    *, project_root: Path, generated_identity: str
) -> tuple[ProjectSkillBundle, ...]:
    """Capture safe canonical project skill bundle bytes and modes."""

    resolved_root: Path = project_root.resolve()
    skills_root: Path = resolved_root
    for part in Path(PROJECT_SKILLS_RELATIVE_PATH).parts:
        skills_root /= part
        if skills_root.is_symlink():
            raise SkillInstallError(f"refusing unsafe project skills source: {skills_root}")
        if not skills_root.exists():
            return ()
        if not skills_root.is_dir():
            raise SkillInstallError(f"project skills source is not a directory: {skills_root}")
    entries: tuple[Path, ...] = tuple(sorted(skills_root.iterdir(), key=lambda path: path.name))
    identities: dict[str, Path] = {}
    bundles: list[ProjectSkillBundle] = []
    for entry in entries:
        if entry.is_symlink() or not entry.is_dir():
            raise SkillInstallError(f"project skill entry must be a regular directory: {entry}")
        _validate_project_skill_identity(identity=entry.name, path=entry)
        normalized: str = entry.name.casefold()
        if normalized == generated_identity.casefold():
            raise SkillInstallError(
                f"duplicate normalized skill identity {entry.name!r} conflicts with "
                "generated guidance"
            )
        if normalized in identities:
            raise SkillInstallError(
                f"duplicate normalized project skill identity: {identities[normalized]} and {entry}"
            )
        identities[normalized] = entry
        files: tuple[ProjectSkillFile, ...] = _discover_project_bundle_files(bundle_root=entry)
        document: ProjectSkillFile | None = next(
            (file for file in files if file.relative_path == Path("SKILL.md")), None
        )
        if document is None:
            raise SkillInstallError(f"project skill bundle has no regular SKILL.md: {entry}")
        document_lines: list[bytes] = document.content.splitlines()
        ownership_prefix: bytes = OWNERSHIP_MARKER_PREFIX.encode("ascii")
        reserved_metadata: bool = PROJECT_SKILL_MARKER.encode("ascii") in document_lines or any(
            line.startswith(ownership_prefix) for line in document_lines
        )
        if reserved_metadata:
            raise SkillInstallError(
                f"canonical project skill contains reserved ownership metadata: {entry}"
            )
        try:
            _ = document.content.decode("utf-8")
        except UnicodeDecodeError as error:
            raise SkillInstallError(f"project skill SKILL.md is not UTF-8: {entry}") from error
        bundles.append(ProjectSkillBundle(identity=entry.name, files=files))
    return tuple(bundles)


def _discover_project_bundle_files(*, bundle_root: Path) -> tuple[ProjectSkillFile, ...]:
    pending: list[Path] = [bundle_root]
    files: list[ProjectSkillFile] = []
    normalized_paths: dict[str, Path] = {}
    while pending:
        directory: Path = pending.pop()
        entries: tuple[Path, ...] = tuple(sorted(directory.iterdir(), key=lambda path: path.name))
        for entry in reversed(entries):
            relative_path: Path = entry.relative_to(bundle_root)
            portable_path: str = relative_path.as_posix()
            try:
                _ = portable_path.encode("utf-8")
            except UnicodeEncodeError as error:
                raise SkillInstallError(
                    f"project skill path is not valid UTF-8: {entry}"
                ) from error
            normalized: str = portable_path.casefold()
            collision: Path | None = normalized_paths.get(normalized)
            if collision is not None:
                raise SkillInstallError(
                    f"project skill bundle has a case-folding path collision: {collision} "
                    f"and {entry}"
                )
            normalized_paths[normalized] = entry
            metadata: os.stat_result = entry.stat(follow_symlinks=False)
            if stat.S_ISLNK(metadata.st_mode):
                raise SkillInstallError(f"project skill content cannot be a symlink: {entry}")
            if stat.S_ISDIR(metadata.st_mode):
                pending.append(entry)
                continue
            if not stat.S_ISREG(metadata.st_mode):
                raise SkillInstallError(f"project skill content must be a regular file: {entry}")
            descriptor: int = os.open(
                entry, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
            )
            with os.fdopen(descriptor, "rb") as source:
                opened: os.stat_result = os.fstat(source.fileno())
                content: bytes = source.read()
                final: os.stat_result = os.fstat(source.fileno())
            stable: tuple[int, ...] = (
                opened.st_dev,
                opened.st_ino,
                opened.st_mode,
                opened.st_size,
                opened.st_mtime_ns,
                opened.st_ctime_ns,
            )
            final_state: tuple[int, ...] = (
                final.st_dev,
                final.st_ino,
                final.st_mode,
                final.st_size,
                final.st_mtime_ns,
                final.st_ctime_ns,
            )
            if stable != final_state or not stat.S_ISREG(final.st_mode):
                raise SkillInstallError(f"project skill content changed during discovery: {entry}")
            files.append(
                ProjectSkillFile(
                    relative_path=relative_path,
                    content=content,
                    mode=stat.S_IMODE(final.st_mode),
                )
            )
    return tuple(sorted(files, key=lambda file: file.relative_path.as_posix()))


def _validate_project_skill_identity(*, identity: str, path: Path) -> None:
    valid: bool = re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", identity) is not None
    reserved: bool = (
        identity in WINDOWS_RESERVED_SKILL_NAMES
        or re.fullmatch(r"(?:com|lpt)[1-9]", identity) is not None
    )
    if not valid or reserved:
        raise SkillInstallError(f"project skill name must be portable ASCII kebab-case: {path}")


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
    publications: tuple[_SkillFilePublication, ...] = tuple(
        _SkillFilePublication(
            snapshot=snapshot, content=content.encode("utf-8"), mode=snapshot.mode
        )
        for snapshot in snapshots
    )
    _write_captured_skill_files(
        publications=publications,
        deletion_snapshots=deletion_snapshots,
        force=force,
        cleanup_roots=tuple(snapshot.path.parent for snapshot in deletion_snapshots),
    )


def write_skill_installation(
    *, plan: SkillInstallPlan, generated_content: bytes, force: bool
) -> None:
    """Synchronize generated guidance and complete project bundles in one transaction."""

    publications: list[_SkillFilePublication] = []
    deletion_snapshots: dict[Path, _SkillFileSnapshot] = {}
    cleanup_roots: set[Path] = set()
    for target in plan.targets:
        root: Path = target.path.parent
        existing: tuple[_SkillFileSnapshot, ...] = _capture_destination_bundle(
            root=root,
            owner=plan.owner,
            identity=plan.context.identity,
            project_bundle=False,
            force=force,
        )
        existing_by_path: dict[Path, _SkillFileSnapshot] = {
            snapshot.path: snapshot for snapshot in existing
        }
        snapshot: _SkillFileSnapshot = existing_by_path.get(target.path) or _capture_skill_file(
            path=target.path, force=True
        )
        publications.append(
            _SkillFilePublication(
                snapshot=snapshot,
                content=generated_content,
                mode=snapshot.mode,
            )
        )
    for target in plan.project_targets:
        cleanup_roots.add(target.path)
        existing = _capture_destination_bundle(
            root=target.path,
            owner=plan.owner,
            identity=target.bundle.identity,
            project_bundle=True,
            force=force,
        )
        existing_by_path = {snapshot.path: snapshot for snapshot in existing}
        desired_paths: set[Path] = set()
        owned_document: bytes = owned_project_skill_content(
            context=plan.context, bundle=target.bundle
        )
        for source_file in target.bundle.files:
            destination: Path = target.path / source_file.relative_path
            desired_paths.add(destination)
            snapshot = existing_by_path.get(destination) or _capture_skill_file(
                path=destination, force=True
            )
            content: bytes = (
                owned_document
                if source_file.relative_path == Path("SKILL.md")
                else source_file.content
            )
            publications.append(
                _SkillFilePublication(
                    snapshot=snapshot,
                    content=content,
                    mode=source_file.mode,
                )
            )
        for snapshot in existing:
            if snapshot.path not in desired_paths:
                deletion_snapshots[snapshot.path] = snapshot
    if plan.synchronize_project_skills:
        desired_identities: frozenset[str] = frozenset(
            (plan.context.identity, *(target.bundle.identity for target in plan.project_targets))
        )
        for skills_directory in {target.path.parent.parent for target in plan.targets}:
            stale_bundles: tuple[tuple[Path, tuple[_SkillFileSnapshot, ...]], ...] = (
                _capture_stale_project_bundles(
                    skills_directory=skills_directory,
                    desired_identities=desired_identities,
                    owner=plan.owner,
                )
            )
            for stale_root, stale_files in stale_bundles:
                cleanup_roots.add(stale_root)
                for snapshot in stale_files:
                    deletion_snapshots[snapshot.path] = snapshot
    for path in plan.legacy_paths:
        legacy: _SkillFileSnapshot | None = _capture_legacy_file(path=path, owner=plan.owner)
        if legacy is not None:
            deletion_snapshots[path] = legacy
            cleanup_roots.add(path.parent)
    _write_captured_skill_files(
        publications=tuple(publications),
        deletion_snapshots=tuple(deletion_snapshots.values()),
        force=True,
        cleanup_roots=tuple(cleanup_roots),
    )


def _write_captured_skill_files(
    *,
    publications: tuple[_SkillFilePublication, ...],
    deletion_snapshots: tuple[_SkillFileSnapshot, ...],
    force: bool,
    cleanup_roots: tuple[Path, ...],
) -> None:
    staged_files: list[_StagedSkillFile] = []
    staged_deletions: list[_StagedSkillDeletion] = []
    published_files: list[_PublishedSkillFile] = []
    published_deletions: list[_PublishedSkillDeletion] = []
    created_directories: list[Path] = []
    completed = False
    try:
        for publication in publications:
            snapshot: _SkillFileSnapshot = publication.snapshot
            created_directories = _create_parent_directories(
                path=snapshot.path.parent, created=created_directories
            )
            _ensure_unchanged(snapshot=snapshot, force=force)
            staged_path: Path = _stage_content(
                destination=snapshot.path,
                content=publication.content,
                mode=publication.mode,
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
        completed = True
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
        if not completed:
            _remove_created_directories(created=created_directories)
    for root in cleanup_roots:
        _remove_empty_bundle_root(root=root)


def _capture_destination_bundle(
    *, root: Path, owner: str, identity: str, project_bundle: bool, force: bool
) -> tuple[_SkillFileSnapshot, ...]:
    _validate_normalization_collision(root / "SKILL.md")
    probe: _SkillFileSnapshot = _capture_skill_file(path=root / "SKILL.md", force=True)
    if not root.exists():
        return ()
    existing: tuple[_SkillFileSnapshot, ...] = _capture_bundle_files(root=root)
    document: _SkillFileSnapshot | None = next(
        (snapshot for snapshot in existing if snapshot.path == root / "SKILL.md"), None
    )
    content: bytes | None = None if document is None else document.content
    ownership: SkillOwnership | None = None if content is None else parse_skill_ownership(content)
    if ownership is not None and (ownership.owner != owner or ownership.identity != identity):
        raise SkillInstallError(
            f"refusing to overwrite skill owned by another Fensu project: {root / 'SKILL.md'}"
        )
    owned: bool = ownership is not None and ownership.owner == owner
    managed: bool = {
        False: owned and content is not None and generated_marker_present(content),
        True: owned and content is not None and project_skill_marker_present(content),
    }[project_bundle]
    compatibility_generated: bool = (
        not project_bundle
        and ownership is None
        and content is not None
        and generated_marker_present(content)
    )
    if not managed and not compatibility_generated and not force:
        raise SkillInstallError(
            f"refusing to overwrite unmanaged skill file: {root / 'SKILL.md'}; rerun with --force"
        )
    if probe.content is not None and document is None:
        raise SkillInstallError(f"skill target changed during update: {probe.path}")
    return existing


def _capture_bundle_files(*, root: Path) -> tuple[_SkillFileSnapshot, ...]:
    if root.is_symlink() or not root.is_dir():
        raise SkillInstallError(f"refusing to write unsafe skill target: {root}")
    pending: list[Path] = [root]
    snapshots: list[_SkillFileSnapshot] = []
    normalized_paths: dict[str, Path] = {}
    while pending:
        directory: Path = pending.pop()
        entries: tuple[Path, ...] = tuple(sorted(directory.iterdir(), key=lambda path: path.name))
        for entry in reversed(entries):
            relative: Path = entry.relative_to(root)
            normalized: str = relative.as_posix().casefold()
            collision: Path | None = normalized_paths.get(normalized)
            if collision is not None:
                raise SkillInstallError(
                    f"skill bundle path normalization collides: {collision} and {entry}"
                )
            normalized_paths[normalized] = entry
            if entry.is_symlink():
                raise SkillInstallError(f"refusing to write unsafe skill target: {entry}")
            if entry.is_dir():
                pending.append(entry)
                continue
            snapshots.append(_capture_skill_file(path=entry, force=True))
    return tuple(sorted(snapshots, key=lambda snapshot: snapshot.path.as_posix()))


def _capture_stale_project_bundles(
    *, skills_directory: Path, desired_identities: frozenset[str], owner: str
) -> tuple[tuple[Path, tuple[_SkillFileSnapshot, ...]], ...]:
    if not skills_directory.exists():
        return ()
    if skills_directory.is_symlink() or not skills_directory.is_dir():
        raise SkillInstallError(f"refusing to inspect unsafe skills directory: {skills_directory}")
    desired_normalized: frozenset[str] = frozenset(
        identity.casefold() for identity in desired_identities
    )
    stale: list[tuple[Path, tuple[_SkillFileSnapshot, ...]]] = []
    for entry in sorted(skills_directory.iterdir(), key=lambda path: path.name):
        if entry.name.casefold() in desired_normalized or entry.is_symlink() or not entry.is_dir():
            continue
        document: _SkillFileSnapshot = _capture_skill_file(path=entry / "SKILL.md", force=True)
        if document.content is None or not project_skill_marker_present(document.content):
            continue
        ownership: SkillOwnership | None = parse_skill_ownership(document.content)
        if ownership is None or ownership.owner != owner or ownership.identity != entry.name:
            continue
        stale.append((entry, _capture_bundle_files(root=entry)))
    return tuple(stale)


def _create_parent_directories(*, path: Path, created: list[Path]) -> list[Path]:
    missing: list[Path] = []
    candidate: Path = path
    while not candidate.exists():
        missing.append(candidate)
        candidate = candidate.parent
    for directory in reversed(missing):
        directory.mkdir()
        created.append(directory)
    return created


def _remove_created_directories(*, created: list[Path]) -> None:
    for directory in reversed(created):
        try:
            directory.rmdir()
        except OSError:
            continue


def _remove_empty_bundle_root(*, root: Path) -> None:
    if root.is_symlink() or not root.is_dir():
        return
    directories: list[Path] = sorted(
        (path for path in root.rglob("*") if path.is_dir()),
        key=lambda path: len(path.parts),
        reverse=True,
    )
    for directory in (*directories, root):
        try:
            directory.rmdir()
        except OSError:
            continue


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
            f"refusing to overwrite skill owned by another Fensu project: {path}"
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
    descriptor, temporary_name = tempfile.mkstemp(prefix=".fensu-skill-", dir=destination.parent)
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
    installed_mode: int = stat.S_IMODE(staged_path.stat().st_mode)
    descriptor: int = os.open(
        snapshot.path,
        os.O_RDWR | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0),
    )
    with os.fdopen(descriptor, "r+b") as target_file:
        _validate_open_skill_file(target_file=target_file, snapshot=snapshot)
        _write_skill_descriptor(target_file=target_file, content=installed_content)
        _set_open_file_mode(target_file=target_file, path=snapshot.path, mode=installed_mode)
    current: _SkillFileSnapshot = _capture_skill_file(
        path=snapshot.path,
        force=True,
        expected_owner=snapshot.expected_owner,
    )
    if (
        current.device != snapshot.device
        or current.inode != snapshot.inode
        or current.content != installed_content
        or current.mode != installed_mode
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
        if published_file.original.mode is not None:
            _set_open_file_mode(
                target_file=target_file,
                path=published_file.installed.path,
                mode=published_file.original.mode,
            )


def _set_open_file_mode(*, target_file: BinaryIO, path: Path, mode: int) -> None:
    if hasattr(os, "fchmod"):
        os.fchmod(target_file.fileno(), mode)
    else:
        path.chmod(mode)


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
        prefix=".fensu-legacy-", dir=staged.snapshot.path.parent
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
