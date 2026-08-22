"""Release metadata validation inputs."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ReleaseDelta:
    """Base and release-head content for generated metadata files."""

    old_version: str
    new_version: str
    changed_paths: frozenset[str]
    base_files: dict[str, str]
    head_files: dict[str, str]
