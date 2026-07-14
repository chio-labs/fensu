"""Normalize repository paths without filesystem observation."""

from functools import cache
from pathlib import Path

from strata.cache.results.constants import (
    PARENT_PATH_PART,
    REPOSITORY_ROOT_PATH,
    WINDOWS_PATH_SEPARATOR,
)
from strata.instrumentation.constants import OPERATION_COUNTERS, RELATIVE_PATH_COMPUTE_OPERATION


@cache
def relative_repository_path(
    *,
    path: Path,
    repo_root: Path,
    allow_root: bool = False,
) -> str | None:
    """Return canonical repository-relative POSIX spelling without resolving paths."""

    OPERATION_COUNTERS.record(operation=RELATIVE_PATH_COMPUTE_OPERATION)
    root: Path = repo_root.absolute()
    candidate: Path = path if path.is_absolute() else root / path
    try:
        relative: Path = candidate.relative_to(root)
    except ValueError:
        return None
    value: str = relative.as_posix()
    if not value or value == REPOSITORY_ROOT_PATH:
        return REPOSITORY_ROOT_PATH if allow_root else None
    if PARENT_PATH_PART in relative.parts or WINDOWS_PATH_SEPARATOR in value:
        return None
    return value
