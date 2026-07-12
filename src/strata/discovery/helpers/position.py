"""Config-driven position facts for files within configured roots."""

from __future__ import annotations

from pathlib import Path

from strata.config.constants import RUNTIME_STRUCTURAL_ROLE_NAMES
from strata.discovery.constants import (
    INIT_MODULE_FILE_NAME,
    MINIMUM_NESTED_PATH_PARTS,
    PYTHON_FILE_SUFFIX,
    ROLE_DIR_NAMES,
    ROLE_FILE_TO_NAME,
)
from strata.discovery.models import ScopedFile
from strata.discovery.types import RoleName, ScopeName


def relative_parts(*, path: Path, root: Path) -> tuple[str, ...]:
    """Return file path parts relative to its configured matching root."""

    return path.resolve().relative_to(root.resolve()).parts


def domain(scoped_file: ScopedFile) -> str | None:
    """Return the top-level domain under the code root, if the file has one."""

    parts: tuple[str, ...] = scoped_file.relative_parts
    if len(parts) == 0 or parts[0].endswith(PYTHON_FILE_SUFFIX):
        return None
    return parts[0]


def subdomain(scoped_file: ScopedFile) -> str | None:
    """Return the subdomain under the domain, excluding role directories."""

    parts: tuple[str, ...] = scoped_file.relative_parts
    if (
        len(parts) < MINIMUM_NESTED_PATH_PARTS
        or parts[1].endswith(PYTHON_FILE_SUFFIX)
        or parts[1] in ROLE_DIR_NAMES
    ):
        return None
    return parts[1]


def role_of(scoped_file: ScopedFile) -> str | None:
    """Return the fixed role for a file by role filename or containing role dir."""

    parts: tuple[str, ...] = scoped_file.relative_parts
    if len(parts) == 0:
        return None
    file_role: str | None = ROLE_FILE_TO_NAME.get(parts[-1])
    if file_role is not None:
        return file_role
    for part in parts[:-1]:
        if scoped_file.scope is ScopeName.TOOLING and part == RoleName.RULES:
            return part
        if part in ROLE_DIR_NAMES:
            return part
    return None


def in_role(*, scoped_file: ScopedFile, role: str) -> bool:
    """Return whether the file belongs to the requested fixed role."""

    return role_of(scoped_file) == role


def is_entry_module(scoped_file: ScopedFile) -> bool:
    """Return whether the first runtime role is main and the file is not an initializer."""

    parts: tuple[str, ...] = scoped_file.relative_parts
    first_role: str | None = _first_runtime_role(parts)
    return first_role == RoleName.MAIN and parts[-1] != INIT_MODULE_FILE_NAME


def is_main_module(scoped_file: ScopedFile) -> bool:
    """Return whether the first runtime structural role is main."""

    return _first_runtime_role(scoped_file.relative_parts) == RoleName.MAIN


def _first_runtime_role(parts: tuple[str, ...]) -> str | None:
    return next((part for part in parts[:-1] if part in RUNTIME_STRUCTURAL_ROLE_NAMES), None)
