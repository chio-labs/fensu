"""Locate the configuration owner from a validated target-local project root."""

from pathlib import Path


def configuration_directory(*, project_root: Path, target_root: str) -> Path:
    """Ascend the normalized relative target path without discovering another repository."""

    directory: Path = project_root
    for _ in Path(target_root).parts:
        directory = directory.parent
    return directory
