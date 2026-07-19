"""Normalize repository paths without filesystem observation."""

from functools import cache
from pathlib import Path

from fensu.cache.results.constants import (
    PARENT_PATH_PART,
    POSIX_PATH_SEPARATOR,
    REPOSITORY_ROOT_PATH,
    WINDOWS_PATH_SEPARATOR,
)
from fensu.discovery.constants import SNAPSHOT_TABLE
from fensu.instrumentation.constants import OPERATION_COUNTERS, RELATIVE_PATH_COMPUTE_OPERATION


@cache
def relative_repository_path(
    *,
    path: Path,
    repo_root: Path,
    allow_root: bool = False,
) -> str | None:
    """Return canonical repository-relative POSIX spelling without resolving paths."""

    snapshot_value: str | None = SNAPSHOT_TABLE.relative_path(path=path, repo_root=repo_root)
    if snapshot_value is not None:
        return snapshot_value
    OPERATION_COUNTERS.record(operation=RELATIVE_PATH_COMPUTE_OPERATION)
    root: Path = repo_root.absolute()
    candidate: Path = path if path.is_absolute() else root / path
    fast_value: str | None = _prefixed_relative_value(candidate=candidate, root=root)
    if fast_value is not None:
        return _validated_value(value=fast_value)
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


def _prefixed_relative_value(*, candidate: Path, root: Path) -> str | None:
    prefix: str = root.as_posix() + POSIX_PATH_SEPARATOR
    candidate_value: str = candidate.as_posix()
    if not candidate_value.startswith(prefix):
        return None
    return candidate_value[len(prefix) :]


def _validated_value(*, value: str) -> str | None:
    if PARENT_PATH_PART in value.split(POSIX_PATH_SEPARATOR) or WINDOWS_PATH_SEPARATOR in value:
        return None
    return value
