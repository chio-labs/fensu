"""Config-driven position facts for files within configured roots."""

from __future__ import annotations

from pathlib import Path

from strata.discovery.core.constants import ROLE_DIR_NAMES, ROLE_FILE_TO_NAME
from strata.discovery.core.models import ScopedFile


def relative_parts(*, path: Path, root: Path) -> tuple[str, ...]:
    """Return file path parts relative to its configured matching root."""

    return path.resolve().relative_to(root.resolve()).parts


def domain(scoped_file: ScopedFile) -> str | None:
    """Return the top-level domain under the code root, if the file has one."""

    parts: tuple[str, ...] = scoped_file.relative_parts
    if len(parts) == 0 or parts[0].endswith(".py"):
        return None
    return parts[0]


def subdomain(scoped_file: ScopedFile) -> str | None:
    """Return the subdomain under the domain, excluding role directories."""

    parts: tuple[str, ...] = scoped_file.relative_parts
    if len(parts) < 2 or parts[1].endswith(".py") or parts[1] in ROLE_DIR_NAMES:
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
        if scoped_file.scope == "tooling" and part == "rules":
            return part
        if part in ROLE_DIR_NAMES:
            return part
    return None


def in_role(*, scoped_file: ScopedFile, role: str) -> bool:
    """Return whether the file belongs to the requested fixed role."""

    return role_of(scoped_file) == role


def is_entry_module(scoped_file: ScopedFile) -> bool:
    """Return whether the file is directly under a main/ package as an entry module."""

    parts: tuple[str, ...] = scoped_file.relative_parts
    if len(parts) < 2 or parts[-2] != "main":
        return False
    return parts[-1] not in {"__init__.py", "main.py"}


def is_main_module(scoped_file: ScopedFile) -> bool:
    """Return whether the file lives anywhere inside a main/ package."""

    return "main" in scoped_file.relative_parts[:-1]
