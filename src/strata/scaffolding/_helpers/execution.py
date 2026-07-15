"""Validated and transactional filesystem execution for initialization."""

from __future__ import annotations

import errno
import json
import os
import stat
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from strata.config.exceptions import ConfigError
from strata.config.main.build_config import build_config
from strata.config.models import Config
from strata.discovery.main.build_project_layout import build_project_layout
from strata.discovery.models import ProjectLayout, RepoRoot
from strata.scaffolding._helpers import capabilities as capabilities_module
from strata.scaffolding._helpers.gitignore import (
    plan_gitignore_update,
    publish_gitignore_update,
)
from strata.scaffolding.constants import (
    CONFIG_FILE_NAME,
    DEFAULT_SELECT,
    PACKAGE_MARKER_FILE_NAME,
    PYTHON_FILE_SUFFIX,
)
from strata.scaffolding.exceptions import InitError
from strata.scaffolding.models import GitIgnorePlan, InitExecution, InitPlan

_READ_CHUNK_SIZE: int = 65_536
_FILE_MODE: int = 0o644


@dataclass(frozen=True, slots=True)
class _PublishedPath:
    path: Path
    device: int
    inode: int
    content: bytes | None
    is_directory: bool


def render_config(*, plan: InitPlan) -> str:
    """Render the minimal deterministic TOML configuration."""

    lines: list[str] = [
        f"roots = {_toml_array(values=plan.roots)}",
        f"tests = {_toml_array(values=plan.tests)}",
    ]
    if plan.tooling:
        lines.append(f"tooling = {_toml_array(values=plan.tooling)}")
    lines.append(f"select = {_toml_array(values=DEFAULT_SELECT)}")
    return "\n".join(lines) + "\n"


def build_rendered_config(*, text: str) -> Config:
    """Round-trip rendered TOML through the public in-memory config builder."""

    raw: object = tomllib.loads(text)
    return build_config(cast("Mapping[str, object]", raw))


def execute_init_plan(*, repository: Path, plan: InitPlan) -> tuple[Config, InitExecution]:
    """Validate and write a config, scaffolding empty roots transactionally."""

    text: str = render_config(plan=plan)
    config: Config = build_rendered_config(text=text)
    _ensure_config_absent(repository=repository)
    gitignore_plan: GitIgnorePlan | None = plan_gitignore_update(
        repository=repository, greenfield=plan.project_name is not None
    )
    created: tuple[_PublishedPath, ...] = ()
    logical_paths: tuple[str, ...] = (
        ()
        if plan.project_name is None
        else (f"src/{plan.project_name}/__init__.py", "tests/.gitkeep")
    )
    config_publication: _PublishedPath | None = None
    try:
        for value in logical_paths:
            created = _create_empty_file(repository=repository, relative=value, created=created)
        _validate_layout(repository=repository, config=config)
        _validate_selected_scope_symlinks(repository=repository, config=config)
        config_publication = _atomic_write_config(repository=repository, text=text)
        if gitignore_plan is not None:
            publish_gitignore_update(repository=repository, plan=gitignore_plan)
    except (ConfigError, InitError, OSError):
        if config_publication is not None:
            _rollback_publication(publication=config_publication)
        _rollback_publications(publications=created)
        raise
    return config, InitExecution(config_path=CONFIG_FILE_NAME, created_paths=logical_paths)


def _validate_layout(*, repository: Path, config: Config) -> None:
    layout: ProjectLayout = build_project_layout(
        config=config, repo_root=RepoRoot(path=repository.resolve())
    )
    _ = layout


def _create_empty_file(
    *, repository: Path, relative: str, created: tuple[_PublishedPath, ...]
) -> tuple[_PublishedPath, ...]:
    if not capabilities_module.supports_dir_fd_operations():
        return _create_empty_file_by_path(
            repository=repository,
            relative=relative,
            created=created,
        )
    path: Path = repository / relative
    _validate_scaffold_path(repository=repository, path=path)
    repository_descriptor: int = _open_repository(repository=repository)
    descriptors: list[int] = [repository_descriptor]
    current_path: Path = repository
    try:
        for part in Path(relative).parts[:-1]:
            parent_descriptor: int = descriptors[-1]
            current_path = current_path / part
            made_directory: bool = False
            try:
                os.mkdir(part, dir_fd=parent_descriptor)
                made_directory = True
            except FileExistsError:
                pass
            directory_descriptor: int = _open_child_directory(
                parent_descriptor=parent_descriptor,
                name=part,
                path=current_path,
            )
            descriptors.append(directory_descriptor)
            if made_directory:
                metadata: os.stat_result = os.fstat(directory_descriptor)
                created = (
                    *created,
                    _publication(path=current_path, metadata=metadata, content=None),
                )
        _verify_directory_walk(
            repository=repository, relative=Path(relative).parent, descriptors=descriptors
        )
        file_name: str = Path(relative).name
        flags: int = (
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_BINARY", 0)
        )
        try:
            descriptor: int = os.open(file_name, flags, _FILE_MODE, dir_fd=descriptors[-1])
        except FileExistsError:
            metadata = os.stat(
                file_name,
                dir_fd=descriptors[-1],
                follow_symlinks=False,
            )
            if not stat.S_ISREG(metadata.st_mode):
                raise InitError(f"Scaffold file path is not a file: {path}") from None
        else:
            try:
                metadata = os.fstat(descriptor)
                _verify_directory_walk(
                    repository=repository,
                    relative=Path(relative).parent,
                    descriptors=descriptors,
                )
            except (InitError, OSError):
                _unlink_at_if_identity(
                    parent_descriptor=descriptors[-1],
                    name=file_name,
                    metadata=os.fstat(descriptor),
                )
                raise
            finally:
                os.close(descriptor)
            created = (*created, _publication(path=path, metadata=metadata, content=b""))
    finally:
        for opened_descriptor in reversed(descriptors):
            os.close(opened_descriptor)
    return created


def _create_empty_file_by_path(
    *, repository: Path, relative: str, created: tuple[_PublishedPath, ...]
) -> tuple[_PublishedPath, ...]:
    path: Path = repository / relative
    _validate_scaffold_path(repository=repository, path=path)
    current: Path = repository
    for part in Path(relative).parts[:-1]:
        current = current / part
        made_directory: bool = False
        try:
            current.mkdir()
            made_directory = True
        except FileExistsError:
            pass
        metadata: os.stat_result = current.lstat()
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise InitError(f"Scaffold directory path is not a directory: {current}")
        _validate_scaffold_path(repository=repository, path=current)
        if made_directory:
            created = (*created, _publication(path=current, metadata=metadata, content=None))
    flags: int = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_BINARY", 0)
    )
    try:
        descriptor: int = os.open(path, flags, _FILE_MODE)
    except FileExistsError:
        metadata = path.lstat()
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
            raise InitError(f"Scaffold file path is not a file: {path}") from None
    else:
        metadata = os.fstat(descriptor)
        try:
            _validate_scaffold_path(repository=repository, path=path)
            _verify_path_identity(path=path, metadata=metadata)
        except (InitError, OSError):
            os.close(descriptor)
            _unlink_path_if_identity(path=path, metadata=metadata)
            raise
        os.close(descriptor)
        created = (*created, _publication(path=path, metadata=metadata, content=b""))
    return created


def _atomic_write_config(*, repository: Path, text: str) -> _PublishedPath:
    _ensure_config_absent(repository=repository)
    if not capabilities_module.supports_dir_fd_operations():
        return _atomic_write_config_by_path(repository=repository, text=text)
    repository_descriptor: int = _open_repository(repository=repository)
    flags: int = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_BINARY", 0)
    )
    try:
        try:
            descriptor: int = os.open(
                CONFIG_FILE_NAME,
                flags,
                _FILE_MODE,
                dir_fd=repository_descriptor,
            )
        except FileExistsError as error:
            raise InitError(
                "Refusing to replace configuration path created concurrently: "
                f"{repository / CONFIG_FILE_NAME}"
            ) from error
        metadata: os.stat_result = os.fstat(descriptor)
        try:
            _write_all(descriptor=descriptor, content=text.encode())
            os.fsync(descriptor)
            _verify_published_file(
                parent_descriptor=repository_descriptor,
                name=CONFIG_FILE_NAME,
                metadata=metadata,
                path=repository / CONFIG_FILE_NAME,
            )
        except (InitError, OSError):
            _unlink_at_if_identity(
                parent_descriptor=repository_descriptor,
                name=CONFIG_FILE_NAME,
                metadata=metadata,
            )
            raise
        finally:
            os.close(descriptor)
    finally:
        os.close(repository_descriptor)
    return _publication(
        path=repository / CONFIG_FILE_NAME,
        metadata=metadata,
        content=text.encode(),
    )


def _atomic_write_config_by_path(*, repository: Path, text: str) -> _PublishedPath:
    path: Path = repository / CONFIG_FILE_NAME
    flags: int = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_BINARY", 0)
    )
    try:
        descriptor: int = os.open(path, flags, _FILE_MODE)
    except FileExistsError as error:
        raise InitError(
            f"Refusing to replace configuration path created concurrently: {path}"
        ) from error
    metadata: os.stat_result = os.fstat(descriptor)
    try:
        _write_all(descriptor=descriptor, content=text.encode())
        os.fsync(descriptor)
        _verify_path_identity(path=path, metadata=metadata)
    except (InitError, OSError):
        os.close(descriptor)
        _unlink_path_if_identity(path=path, metadata=metadata)
        raise
    os.close(descriptor)
    return _publication(path=path, metadata=metadata, content=text.encode())


def _ensure_config_absent(*, repository: Path) -> None:
    path: Path = repository / CONFIG_FILE_NAME
    if path.is_symlink() or path.exists():
        raise InitError(f"Refusing to replace existing configuration path: {path}")


def _validate_selected_scope_symlinks(*, repository: Path, config: Config) -> None:
    values: tuple[str, ...] = (*config.roots, *config.tests, *config.tooling)
    for value in values:
        scope: Path = repository / value
        _validate_scope_path(repository=repository, scope=scope, value=value)
        if not scope.is_dir():
            continue
        for current_text, directories, files in os.walk(scope, followlinks=False):
            current: Path = Path(current_text)
            names: tuple[str, ...] = (*directories, *files)
            for name in names:
                candidate: Path = current / name
                if candidate.is_symlink() and (
                    candidate.suffix == PYTHON_FILE_SUFFIX
                    or candidate.name == PACKAGE_MARKER_FILE_NAME
                ):
                    raise InitError(f"Selected scope contains a symlinked Python path: {candidate}")
            directories[:] = [name for name in directories if not (current / name).is_symlink()]


def _validate_scope_path(*, repository: Path, scope: Path, value: str) -> None:
    current: Path = repository
    for part in scope.relative_to(repository).parts:
        current = current / part
        if current.is_symlink():
            raise InitError(f"Selected scope traverses a symlink: {value} ({current})")


def _validate_scaffold_path(*, repository: Path, path: Path) -> None:
    repository_resolved: Path = repository.resolve(strict=True)
    repository_metadata: os.stat_result = repository.lstat()
    if stat.S_ISLNK(repository_metadata.st_mode):
        raise InitError(f"Refusing to scaffold through symlink path: {repository}")
    relative: Path = path.relative_to(repository)
    current: Path = repository
    for part in relative.parts:
        current = current / part
        try:
            metadata: os.stat_result = current.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(metadata.st_mode):
            raise InitError(f"Refusing to scaffold through symlink path: {current}")
        if not current.resolve(strict=False).is_relative_to(repository_resolved):
            raise InitError(f"Refusing to scaffold outside repository: {current}")


def _open_repository(*, repository: Path) -> int:
    flags: int = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor: int = os.open(repository, flags)
    metadata: os.stat_result = os.fstat(descriptor)
    path_metadata: os.stat_result = repository.lstat()
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or stat.S_ISLNK(path_metadata.st_mode)
        or metadata.st_dev != path_metadata.st_dev
        or metadata.st_ino != path_metadata.st_ino
    ):
        os.close(descriptor)
        raise InitError(f"Repository path is not a stable directory: {repository}")
    return descriptor


def _open_child_directory(*, parent_descriptor: int, name: str, path: Path) -> int:
    flags: int = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor: int = os.open(name, flags, dir_fd=parent_descriptor)
    except OSError as error:
        if error.errno in (errno.ELOOP, errno.ENOTDIR):
            raise InitError(f"Scaffold directory path is not a directory: {path}") from error
        raise
    metadata: os.stat_result = os.fstat(descriptor)
    linked: os.stat_result = os.stat(name, dir_fd=parent_descriptor, follow_symlinks=False)
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or stat.S_ISLNK(linked.st_mode)
        or metadata.st_dev != linked.st_dev
        or metadata.st_ino != linked.st_ino
    ):
        os.close(descriptor)
        raise InitError(f"Scaffold directory path changed concurrently: {path}")
    return descriptor


def _verify_directory_walk(*, repository: Path, relative: Path, descriptors: list[int]) -> None:
    repository_metadata: os.stat_result = repository.lstat()
    opened_repository: os.stat_result = os.fstat(descriptors[0])
    if (
        stat.S_ISLNK(repository_metadata.st_mode)
        or repository_metadata.st_dev != opened_repository.st_dev
        or repository_metadata.st_ino != opened_repository.st_ino
    ):
        raise InitError(f"Repository path changed concurrently: {repository}")
    for index, name in enumerate(relative.parts, start=1):
        linked: os.stat_result = os.stat(
            name,
            dir_fd=descriptors[index - 1],
            follow_symlinks=False,
        )
        opened: os.stat_result = os.fstat(descriptors[index])
        if (
            stat.S_ISLNK(linked.st_mode)
            or linked.st_dev != opened.st_dev
            or linked.st_ino != opened.st_ino
        ):
            raise InitError(
                f"Scaffold directory path changed concurrently: {repository / relative}"
            )


def _verify_published_file(
    *, parent_descriptor: int, name: str, metadata: os.stat_result, path: Path
) -> None:
    published: os.stat_result = os.stat(name, dir_fd=parent_descriptor, follow_symlinks=False)
    if (
        not stat.S_ISREG(metadata.st_mode)
        or not stat.S_ISREG(published.st_mode)
        or published.st_dev != metadata.st_dev
        or published.st_ino != metadata.st_ino
    ):
        raise InitError(f"Published path changed concurrently: {path}")


def _verify_path_identity(*, path: Path, metadata: os.stat_result) -> None:
    published: os.stat_result = path.lstat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or not stat.S_ISREG(published.st_mode)
        or published.st_dev != metadata.st_dev
        or published.st_ino != metadata.st_ino
    ):
        raise InitError(f"Published path changed concurrently: {path}")


def _unlink_at_if_identity(*, parent_descriptor: int, name: str, metadata: os.stat_result) -> None:
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


def _publication(*, path: Path, metadata: os.stat_result, content: bytes | None) -> _PublishedPath:
    return _PublishedPath(
        path=path,
        device=metadata.st_dev,
        inode=metadata.st_ino,
        content=content,
        is_directory=content is None,
    )


def _rollback_publications(*, publications: tuple[_PublishedPath, ...]) -> None:
    for publication in reversed(publications):
        _rollback_publication(publication=publication)


def _rollback_publication(*, publication: _PublishedPath) -> None:
    try:
        metadata: os.stat_result = publication.path.lstat()
    except FileNotFoundError:
        return
    if metadata.st_dev != publication.device or metadata.st_ino != publication.inode:
        return
    if publication.is_directory:
        try:
            publication.path.rmdir()
        except OSError as error:
            if error.errno not in (errno.ENOENT, errno.ENOTEMPTY):
                raise
        return
    try:
        descriptor: int = os.open(
            publication.path,
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0),
        )
    except OSError as error:
        if error.errno in (errno.ELOOP, errno.ENOENT):
            return
        raise
    try:
        opened: os.stat_result = os.fstat(descriptor)
        if opened.st_dev != publication.device or opened.st_ino != publication.inode:
            return
        content: bytes = _read_all(descriptor=descriptor)
    finally:
        os.close(descriptor)
    if content != publication.content:
        return
    try:
        current: os.stat_result = publication.path.lstat()
    except FileNotFoundError:
        return
    if current.st_dev == publication.device and current.st_ino == publication.inode:
        publication.path.unlink()


def _read_all(*, descriptor: int) -> bytes:
    chunks: list[bytes] = []
    while True:
        chunk: bytes = os.read(descriptor, _READ_CHUNK_SIZE)
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)


def _write_all(*, descriptor: int, content: bytes) -> None:
    remaining: memoryview = memoryview(content)
    while remaining:
        written: int = os.write(descriptor, remaining)
        if not written:
            raise InitError("Could not complete configuration write.")
        remaining = remaining[written:]


def _toml_array(*, values: tuple[str, ...]) -> str:
    return "[" + ", ".join(json.dumps(value) for value in values) + "]"
