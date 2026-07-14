"""Match root comments, negation, anchors, directories, and ordinary globs conservatively."""

from __future__ import annotations

import errno
import fnmatch
import os
import stat
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from strata.cache.storage.constants import CACHE_DATABASE_RELATIVE_PATH
from strata.scaffolding._helpers import capabilities as capabilities_module
from strata.scaffolding.constants import (
    GITIGNORE_FILE_NAME,
    GLOBSTAR_PATTERN,
    POSIX_PATH_SEPARATOR,
    PYTHON_GITIGNORE_TEMPLATE,
    STRATA_GITIGNORE_BLOCK,
)
from strata.scaffolding.exceptions import InitError
from strata.scaffolding.models import GitIgnorePlan
from strata.scaffolding.types import GitIgnorePredicate


@dataclass(frozen=True, slots=True)
class _IgnoreRule:
    pattern: str
    negated: bool
    anchored: bool
    directory_only: bool


_READ_CHUNK_SIZE: int = 65_536
_FILE_MODE: int = 0o644


def is_gitignored(*, repository: Path, path: Path, is_directory: bool) -> bool:
    """Apply a documented stdlib subset of root .gitignore rules in declaration order."""

    predicate: GitIgnorePredicate = build_gitignore_predicate(repository=repository)
    return predicate(path=path, is_directory=is_directory)


def build_gitignore_predicate(*, repository: Path) -> GitIgnorePredicate:
    """Parse root rules once and return an immutable detection-pass predicate."""

    rules: tuple[_IgnoreRule, ...] = _load_rules(repository=repository)

    def is_ignored(*, path: Path, is_directory: bool) -> bool:
        try:
            relative: PurePosixPath = PurePosixPath(path.relative_to(repository).as_posix())
        except ValueError:
            return True
        ignored: bool = False
        for rule in rules:
            if _matches(rule=rule, relative=relative, is_directory=is_directory):
                ignored = not rule.negated
        return ignored

    return is_ignored


def plan_gitignore_update(*, repository: Path, greenfield: bool) -> GitIgnorePlan | None:
    """Capture a safe root gitignore update unless the cache path is already covered."""

    path: Path = repository / GITIGNORE_FILE_NAME
    captured: tuple[bytes, os.stat_result] | None = _capture_regular_file(path=path)
    if captured is None:
        prefix: bytes = PYTHON_GITIGNORE_TEMPLATE if greenfield else b""
        return GitIgnorePlan(
            original=None,
            desired=prefix + STRATA_GITIGNORE_BLOCK,
            device=None,
            inode=None,
        )
    original, metadata = captured
    rules: tuple[_IgnoreRule, ...] = _rules_from_content(content=original)
    ignored: bool = _is_ignored_by_rules(
        repository=repository,
        path=repository / CACHE_DATABASE_RELATIVE_PATH,
        is_directory=False,
        rules=rules,
    )
    if ignored:
        return None
    separator: bytes = b"" if not original or original.endswith(b"\n") else b"\n"
    return GitIgnorePlan(
        original=original,
        desired=original + separator + STRATA_GITIGNORE_BLOCK,
        device=metadata.st_dev,
        inode=metadata.st_ino,
    )


def publish_gitignore_update(*, repository: Path, plan: GitIgnorePlan) -> None:
    """Publish a captured gitignore update without replacing concurrent user content."""

    path: Path = repository / GITIGNORE_FILE_NAME
    if plan.original is None:
        _publish_new_gitignore(repository=repository, path=path, desired=plan.desired)
        return
    flags: int = os.O_RDWR | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0)
    descriptor: int = os.open(path, flags)
    appended: bool = False
    try:
        metadata: os.stat_result = os.fstat(descriptor)
        current: bytes = os.read(descriptor, len(plan.original) + 1)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_dev != plan.device
            or metadata.st_ino != plan.inode
            or current != plan.original
        ):
            raise InitError(f"Refusing to replace root gitignore changed concurrently: {path}")
        suffix: bytes = plan.desired[len(plan.original) :]
        _write_all(descriptor=descriptor, content=suffix)
        appended = True
        os.fsync(descriptor)
        published: os.stat_result = path.lstat()
        if published.st_dev != metadata.st_dev or published.st_ino != metadata.st_ino:
            raise InitError(f"Refusing root gitignore path replaced concurrently: {path}")
    except (InitError, OSError):
        if appended:
            _rollback_descriptor_update(descriptor=descriptor, plan=plan)
        raise
    finally:
        os.close(descriptor)


def _publish_new_gitignore(*, repository: Path, path: Path, desired: bytes) -> None:
    flags: int = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    if not capabilities_module.supports_dir_fd_operations():
        _publish_new_gitignore_by_path(path=path, desired=desired, flags=flags)
        return
    repository_descriptor: int = _open_repository(repository=repository)
    try:
        try:
            descriptor: int = os.open(
                GITIGNORE_FILE_NAME,
                flags,
                _FILE_MODE,
                dir_fd=repository_descriptor,
            )
        except FileExistsError as error:
            raise InitError(f"Refusing root gitignore path created concurrently: {path}") from error
        metadata: os.stat_result = os.fstat(descriptor)
        try:
            _write_all(descriptor=descriptor, content=desired)
            os.fsync(descriptor)
            published: os.stat_result = os.stat(
                GITIGNORE_FILE_NAME,
                dir_fd=repository_descriptor,
                follow_symlinks=False,
            )
            if (
                not stat.S_ISREG(metadata.st_mode)
                or not stat.S_ISREG(published.st_mode)
                or published.st_dev != metadata.st_dev
                or published.st_ino != metadata.st_ino
            ):
                raise InitError(f"Refusing root gitignore path replaced concurrently: {path}")
        except (InitError, OSError):
            _unlink_if_identity(
                parent_descriptor=repository_descriptor,
                name=GITIGNORE_FILE_NAME,
                metadata=metadata,
            )
            raise
        finally:
            os.close(descriptor)
    finally:
        os.close(repository_descriptor)


def _publish_new_gitignore_by_path(*, path: Path, desired: bytes, flags: int) -> None:
    try:
        descriptor: int = os.open(path, flags, _FILE_MODE)
    except FileExistsError as error:
        raise InitError(f"Refusing root gitignore path created concurrently: {path}") from error
    metadata: os.stat_result = os.fstat(descriptor)
    try:
        _write_all(descriptor=descriptor, content=desired)
        os.fsync(descriptor)
        published: os.stat_result = path.lstat()
        if (
            not stat.S_ISREG(metadata.st_mode)
            or not stat.S_ISREG(published.st_mode)
            or published.st_dev != metadata.st_dev
            or published.st_ino != metadata.st_ino
        ):
            raise InitError(f"Refusing root gitignore path replaced concurrently: {path}")
    except (InitError, OSError):
        _unlink_path_if_identity(path=path, metadata=metadata)
        raise
    finally:
        os.close(descriptor)


def _open_repository(*, repository: Path) -> int:
    flags: int = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor: int = os.open(repository, flags)
    metadata: os.stat_result = os.fstat(descriptor)
    linked: os.stat_result = repository.lstat()
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or stat.S_ISLNK(linked.st_mode)
        or metadata.st_dev != linked.st_dev
        or metadata.st_ino != linked.st_ino
    ):
        os.close(descriptor)
        raise InitError(f"Repository path is not a stable directory: {repository}")
    return descriptor


def _unlink_if_identity(*, parent_descriptor: int, name: str, metadata: os.stat_result) -> None:
    try:
        current: os.stat_result = os.stat(
            name,
            dir_fd=parent_descriptor,
            follow_symlinks=False,
        )
    except FileNotFoundError:
        return
    if current.st_dev == metadata.st_dev and current.st_ino == metadata.st_ino:
        os.unlink(name, dir_fd=parent_descriptor)


def _unlink_path_if_identity(*, path: Path, metadata: os.stat_result) -> None:
    try:
        current: os.stat_result = path.lstat()
    except FileNotFoundError:
        return
    if current.st_dev == metadata.st_dev and current.st_ino == metadata.st_ino:
        path.unlink()


def _write_all(*, descriptor: int, content: bytes) -> None:
    remaining: memoryview = memoryview(content)
    while remaining:
        written: int = os.write(descriptor, remaining)
        if not written:
            raise InitError("Could not complete root gitignore write.")
        remaining = remaining[written:]


def _rollback_descriptor_update(*, descriptor: int, plan: GitIgnorePlan) -> None:
    if plan.original is None:
        return
    _ = os.lseek(descriptor, 0, os.SEEK_SET)
    current: bytes = os.read(descriptor, len(plan.desired) + 1)
    if current != plan.desired:
        return
    os.ftruncate(descriptor, len(plan.original))
    os.fsync(descriptor)


def _load_rules(*, repository: Path) -> tuple[_IgnoreRule, ...]:
    path: Path = repository / GITIGNORE_FILE_NAME
    captured: tuple[bytes, os.stat_result] | None = _capture_regular_file(path=path)
    if captured is None:
        return ()
    content, _ = captured
    return _rules_from_content(content=content)


def _rules_from_content(*, content: bytes) -> tuple[_IgnoreRule, ...]:
    rules: list[_IgnoreRule] = []
    for source_line in content.decode("utf-8").splitlines():
        rule: _IgnoreRule | None = _parse_rule(source_line=source_line)
        if rule is not None:
            rules.append(rule)
    return tuple(rules)


def _parse_rule(*, source_line: str) -> _IgnoreRule | None:
    line: str = source_line
    if not line or line.startswith("#"):
        return None
    negated: bool = line.startswith("!")
    if negated:
        line = line[1:]
    elif line.startswith(r"\#") or line.startswith(r"\!"):
        line = line[1:]
    anchored: bool = line.startswith("/")
    if anchored:
        line = line[1:]
    directory_only: bool = line.endswith("/")
    pattern: str = line.rstrip("/")
    if not pattern:
        return None
    return _IgnoreRule(
        pattern=pattern,
        negated=negated,
        anchored=anchored,
        directory_only=directory_only,
    )


def _capture_regular_file(*, path: Path) -> tuple[bytes, os.stat_result] | None:
    if path.is_symlink():
        raise InitError(f"Root gitignore path is not a regular file: {path}")
    try:
        descriptor: int = os.open(
            path,
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0),
        )
    except FileNotFoundError:
        return None
    except OSError as error:
        if error.errno == errno.ELOOP:
            raise InitError(f"Root gitignore path is not a regular file: {path}") from error
        if error.errno in {errno.EACCES, errno.EISDIR} and path.is_dir():
            raise InitError(f"Root gitignore path is not a regular file: {path}") from error
        raise
    try:
        metadata: os.stat_result = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise InitError(f"Root gitignore path is not a regular file: {path}")
        return _read_descriptor(descriptor=descriptor), metadata
    finally:
        os.close(descriptor)


def _read_descriptor(*, descriptor: int) -> bytes:
    chunks: list[bytes] = []
    while True:
        chunk: bytes = os.read(descriptor, _READ_CHUNK_SIZE)
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)


def _is_ignored_by_rules(
    *,
    repository: Path,
    path: Path,
    is_directory: bool,
    rules: tuple[_IgnoreRule, ...],
) -> bool:
    try:
        relative: PurePosixPath = PurePosixPath(path.relative_to(repository).as_posix())
    except ValueError:
        return True
    ignored: bool = False
    for rule in rules:
        if _matches(rule=rule, relative=relative, is_directory=is_directory):
            ignored = not rule.negated
    return ignored


def _matches(*, rule: _IgnoreRule, relative: PurePosixPath, is_directory: bool) -> bool:
    candidates: tuple[str, ...] = _match_candidates(
        relative=relative,
        include_self=is_directory or not rule.directory_only,
    )
    if rule.anchored or POSIX_PATH_SEPARATOR in rule.pattern:
        return any(
            _path_pattern_matches(candidate=candidate, pattern=rule.pattern)
            for candidate in candidates
        )
    return any(
        fnmatch.fnmatchcase(PurePosixPath(candidate).name, rule.pattern) for candidate in candidates
    )


def _match_candidates(*, relative: PurePosixPath, include_self: bool) -> tuple[str, ...]:
    parts: tuple[str, ...] = relative.parts
    limit: int = len(parts) if include_self else len(parts) - 1
    return tuple(PurePosixPath(*parts[:index]).as_posix() for index in range(1, limit + 1))


def _path_pattern_matches(*, candidate: str, pattern: str) -> bool:
    path_parts: tuple[str, ...] = PurePosixPath(candidate).parts
    pattern_parts: tuple[str, ...] = PurePosixPath(pattern).parts
    return _segment_pattern_matches(path_parts=path_parts, pattern_parts=pattern_parts)


def _segment_pattern_matches(
    *, path_parts: tuple[str, ...], pattern_parts: tuple[str, ...]
) -> bool:
    if not pattern_parts:
        return not path_parts
    pattern_head: str = pattern_parts[0]
    if pattern_head == GLOBSTAR_PATTERN:
        remaining_pattern: tuple[str, ...] = pattern_parts[1:]
        if _segment_pattern_matches(path_parts=path_parts, pattern_parts=remaining_pattern):
            return True
        return bool(path_parts) and _segment_pattern_matches(
            path_parts=path_parts[1:], pattern_parts=pattern_parts
        )
    if not path_parts or not fnmatch.fnmatchcase(path_parts[0], pattern_head):
        return False
    return _segment_pattern_matches(path_parts=path_parts[1:], pattern_parts=pattern_parts[1:])
