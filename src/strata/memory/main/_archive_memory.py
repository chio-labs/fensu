"""Archive canonical Strata Memory sources internally."""

from __future__ import annotations

from pathlib import Path

from strata.config.main.load_project_config import load_project_config
from strata.config.models import LoadedConfig
from strata.memory._helpers.native_operations import archive
from strata.memory._helpers.project import resolve_memory_project
from strata.memory.models import MemoryArchiveResult, MemoryProject


def archive_memory(*, paths: tuple[str, ...], confirmed: bool) -> MemoryArchiveResult:
    """Archive explicit sources or eligible terminal tasks and synchronize memory."""

    project: MemoryProject = resolve_memory_project()
    loaded: LoadedConfig = load_project_config(Path.cwd())
    return archive(
        project=project,
        requested_paths=paths,
        archive_after_days=loaded.config.memory.tasks.archive_after_days,
        confirmed=confirmed,
    )
