"""Atomic repository-local persistent cache storage."""

from __future__ import annotations

import os
import secrets
import stat
from pathlib import Path
from typing import BinaryIO

from strata.cache.storage.constants import (
    CACHE_FILE_MODE,
    CACHE_TEMPORARY_SUFFIX,
    CACHE_VERSION_RELATIVE_PATH,
    DIRECTORY_OPEN_FLAGS,
    FILE_READ_FLAGS,
    FILE_WRITE_FLAGS,
    PARENT_PATH_PART,
    SECURE_CACHE_IO_SUPPORTED,
)
from strata.cache.storage.exceptions import CachePathError, CacheRecordError
from strata.cache.storage.helpers.serialization import decode_cache_record, encode_cache_record
from strata.cache.storage.models import CacheRecord


class CacheStore:
    """Read and atomically publish disposable versioned cache records."""

    def __init__(self, *, repo_root: Path) -> None:
        """Bind storage without creating the cache directory."""

        self._repo_root: Path = repo_root.resolve()
        self._root: Path = self._repo_root / CACHE_VERSION_RELATIVE_PATH

    @property
    def root(self) -> Path:
        """Return the active versioned cache root."""

        return self._root

    def read(self, *, relative_path: Path, expected_kind: str) -> CacheRecord | None:
        """Return a validated record or None for a miss, corruption, or read failure."""

        self._validate_relative_path(relative_path)
        if not SECURE_CACHE_IO_SUPPORTED:
            return None
        parent_descriptor: int | None = None
        file_descriptor: int | None = None
        try:
            parent_descriptor = self._open_parent(relative_path=relative_path, create=False)
            file_descriptor = os.open(
                relative_path.name,
                FILE_READ_FLAGS,
                dir_fd=parent_descriptor,
            )
            if not stat.S_ISREG(os.fstat(file_descriptor).st_mode):
                return None
            file: BinaryIO = os.fdopen(file_descriptor, "rb")
            file_descriptor = None
            with file:
                data: bytes = file.read()
        except (OSError, RuntimeError):
            return None
        finally:
            _close_descriptor(file_descriptor)
            _close_descriptor(parent_descriptor)
        return decode_cache_record(data, expected_kind=expected_kind)

    def write(self, *, relative_path: Path, record: CacheRecord) -> bool:
        """Atomically publish a record, returning False when storage is unavailable."""

        self._validate_relative_path(relative_path)
        if not SECURE_CACHE_IO_SUPPORTED:
            return False
        parent_descriptor: int | None = None
        file_descriptor: int | None = None
        temporary_name: str | None = None
        try:
            data: bytes = encode_cache_record(record)
            parent_descriptor = self._open_parent(relative_path=relative_path, create=True)
            temporary_name = f".{relative_path.name}.{secrets.token_hex(8)}{CACHE_TEMPORARY_SUFFIX}"
            file_descriptor = os.open(
                temporary_name,
                FILE_WRITE_FLAGS,
                CACHE_FILE_MODE,
                dir_fd=parent_descriptor,
            )
            file: BinaryIO = os.fdopen(file_descriptor, "wb")
            file_descriptor = None
            with file:
                file.write(data)
                file.flush()
                os.fsync(file.fileno())
            os.replace(
                temporary_name,
                relative_path.name,
                src_dir_fd=parent_descriptor,
                dst_dir_fd=parent_descriptor,
            )
            temporary_name = None
        except (CacheRecordError, OSError, RuntimeError):
            return False
        finally:
            _close_descriptor(file_descriptor)
            _remove_temporary_file(name=temporary_name, parent_descriptor=parent_descriptor)
            _close_descriptor(parent_descriptor)
        return True

    def _validate_relative_path(self, relative_path: Path) -> None:
        if (
            relative_path.is_absolute()
            or not relative_path.parts
            or PARENT_PATH_PART in relative_path.parts
        ):
            raise CachePathError(
                f"Cache entry path must stay below the cache root: {relative_path}"
            )

    def _open_parent(self, *, relative_path: Path, create: bool) -> int:
        directory_parts: tuple[str, ...] = (
            *CACHE_VERSION_RELATIVE_PATH.parts,
            *relative_path.parent.parts,
        )
        descriptor: int = os.open(self._repo_root, DIRECTORY_OPEN_FLAGS)
        try:
            for part in directory_parts:
                if create:
                    _create_directory(name=part, parent_descriptor=descriptor)
                child_descriptor: int = os.open(
                    part,
                    DIRECTORY_OPEN_FLAGS,
                    dir_fd=descriptor,
                )
                _close_descriptor(descriptor)
                descriptor = child_descriptor
        except OSError:
            _close_descriptor(descriptor)
            raise
        return descriptor


def _create_directory(*, name: str, parent_descriptor: int) -> None:
    try:
        os.mkdir(name, dir_fd=parent_descriptor)
    except FileExistsError:
        return


def _remove_temporary_file(*, name: str | None, parent_descriptor: int | None) -> None:
    if name is None or parent_descriptor is None:
        return
    try:
        os.unlink(name, dir_fd=parent_descriptor)
    except OSError:
        return


def _close_descriptor(descriptor: int | None) -> None:
    try:
        if descriptor is not None:
            os.close(descriptor)
    except OSError:
        return
